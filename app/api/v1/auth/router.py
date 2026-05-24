from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta, timezone
from typing import Annotated

from sqlalchemy.orm import selectinload

from app.schemas.tenant import (
    Register,
    RegisterTenantResponse,
    Token,
    ChangePasswordRequest
)
from app.schemas.users import (
    CurrentUserResponse,
    MembershipSummary,
)

from app.api.v1.auth.services import register_tenant_service

from app.core.database import get_db
from app.core.dependencies.session import CurrentSession
from app.core.security import (
    hash_password,
    hash_token,
    verify_password,
    create_access_token,
    create_refresh_token,
)
from app.core.dependencies.auth import CurrentAuth
from app.models.user import Membership, User, UserSession
from app.core.config import settings
from app.models import User


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

# POST -> /auth/register-tenant
@router.post(
    "/register-tenant",
    response_model=RegisterTenantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_tenant(
    payload: Register,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Register a new tenant and its owner user account"""
    try:
        result = await register_tenant_service(
            db=db,
            payload=payload,
        )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenant or email already exists.",
        )
        
# POST -> /auth/token
@router.post('/token', response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Login endpoint for JWT authentication.
    """
    # Find user
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.memberships)
            .selectinload(Membership.role)
        )
        .where(
            func.lower(User.email) == form_data.username.lower()
        )
    )

    user = result.scalar_one_or_none()

    # Validate credentials
    if not user or not verify_password(
        form_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check user status
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Optional email verification check
    # if not user.is_verified:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Email not verified",
    #     )

    # Get active membership
    membership = next(
        (
            membership
            for membership in user.memberships
            if membership.is_active
        ),
        None,
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active tenant membership found",
        )

    # Create access token
    access_token = create_access_token(
        user_id=user.id,
        tenant_id=membership.tenant_id,
        role=membership.role.name,
    )
    # Create refresh token
    refresh_token = create_refresh_token(
    user_id=user.id,
    )
    # Store refresh token in DB
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    await db.commit()

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    
# POST -> /auth/refresh
@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    current_session: CurrentSession,
    db: AsyncSession = Depends(get_db),
):
    """
    Rotate refresh token and issue new access token.
    """
    
    user_id = current_session.payload["sub"]
    session = current_session.session

    # Load user and memberships
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.memberships)
            .selectinload(Membership.role),

            selectinload(User.memberships)
            .selectinload(Membership.tenant),
        )
        .where(User.id == user_id)
    )

    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Validate user status
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Find active membership
    membership = next(
        (
            membership
            for membership in user.memberships
            if membership.is_active
            and membership.tenant.is_active
        ),
        None,
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active tenant membership found",
        )
        
    # revoke old session
    session.is_revoked = True
    session.revoked_at = datetime.now(timezone.utc)

    # new tokens
    access_token = create_access_token(
        user_id=user.id,
        tenant_id=membership.tenant_id,
        role=membership.role.name,
    )
    refresh_token = create_refresh_token(
        user_id=user.id,
    )
    
    # Store new refresh token session
    new_session = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )

    db.add(new_session)
    await db.commit()


    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    
    
# POST -> /auth/logout
@router.post("/logout")
async def logout(
    current_session: CurrentSession,
    auth: CurrentAuth,
    db: AsyncSession = Depends(get_db),
):
    """
    Logout current device/session.
    """

    if current_session.session.user_id != auth.user.id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden",
        )

    current_session.session.is_revoked = True
    current_session.session.revoked_at = datetime.now(timezone.utc)

    await db.commit()

    return {
        "message": "Logged out successfully",
    }
    
    
# POST -> /auth/logout-all
@router.post("/logout-all")
async def logout_all(
    auth: CurrentAuth,
    db: AsyncSession = Depends(get_db),
):
    """
    Logout from all devices.
    """

    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == auth.user.id,
            UserSession.is_revoked.is_(False),
        )
    )

    sessions = result.scalars().all()
    if not sessions:
        raise HTTPException(
            status_code=404,
            detail="No active sessions found",
        )

    now = datetime.now(timezone.utc)

    for session in sessions:
        session.is_revoked = True
        session.revoked_at = now

    await db.commit()

    return {
        "status_code": status.HTTP_200_OK,
        "message": "Logged out from all devices",
    }
    
    
# GET -> /auth/me
@router.get(
    "/me",
    response_model=CurrentUserResponse,
)
async def me(
    auth: CurrentAuth,
):
    """Get current user info, including memberships and permissions"""
    memberships = []
    permissions = set()

    memberships.append(
        MembershipSummary(
            tenant=auth.membership.tenant,
            role=auth.membership.role.name,
            is_active=auth.membership.is_active,
        )
    )

    for role_permission in auth.membership.role.permissions:
        permissions.add(
            role_permission.permission.name
        )

    return CurrentUserResponse(
        id=auth.user.id,
        email=auth.user.email,
        username=auth.user.username,
        phone_number=auth.user.phone_number,
        is_active=auth.user.is_active,
        is_verified=auth.user.is_verified,

        tenant=auth.membership.tenant,
        role=auth.membership.role.name,
        permissions=sorted(list(permissions)),
    )
    
# POST -> /auth/change-password
@router.post("/password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: ChangePasswordRequest,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if not verify_password(password_data.current_password, auth.user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    auth.user.hashed_password = hash_password(password_data.new_password)
    await db.commit()
    return {
        "message": "Password Changed successfully"
    }