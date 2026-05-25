from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.models.user import (
    User,
    Membership,
    Role,
    RolePermission
)

from app.schemas.users import UserDetail, UserListItem, UserCreate, MembershipSummary, TenantSummary, UserUpdate

def tenant_user_query(tenant_id: UUID):
    return (
        select(User)
        .join(Membership)
        .where(
            Membership.tenant_id == tenant_id,
            Membership.is_active.is_(True),
        )
        .options(
            selectinload(User.memberships)
            .selectinload(Membership.role),

            selectinload(User.memberships)
            .selectinload(Membership.tenant),
        )
    )

async def get_tenant_users(
    db: AsyncSession,
    tenant_id: UUID,
    role: str | None = None,
) -> list[UserListItem]:

    query = tenant_user_query(tenant_id)

    # role filter
    if role:
        query = query.join(Role).where(
            Role.name == role,
            Role.tenant_id.is_(None),
        )

    result = await db.execute(query)
    users = result.scalars().unique().all()

    response: list[UserListItem] = []
    for user in users:
        membership = next(
            (
                membership
                for membership in user.memberships
                if membership.tenant_id == tenant_id
            ),
            None,
        )

        if not membership:
            continue

        response.append(
            UserListItem(
                id=user.id,
                email=user.email,
                username=user.username,
                phone_number=user.phone_number,
                is_active=user.is_active,
                is_verified=user.is_verified,
                role=membership.role.name,
            )
        )

    return response

async def create_tenant_user(
    db: AsyncSession,
    payload: UserCreate,
    tenant_id: UUID,
) -> UserListItem:
    """Create a new user and return the created user details"""
    result = await db.execute(
        select(User).where(
            func.lower(User.email) == payload.email.lower()
        )
    )
    
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise ValueError("A user with this email already exists.")
    
    # Create new user
    new_user = User(
        email=payload.email,
        username=payload.username,
        phone_number=payload.phone_number,
        hashed_password=hash_password(payload.password),
        is_active=True,
        is_verified=False,
    )
    db.add(new_user)
    await db.flush()  # Flush to get the new user's ID
    
    # Get Role
    role_result = await db.execute(
        select(Role).where(
            Role.name == payload.role,
            Role.tenant_id.is_(None),
        )
    )

    role = role_result.scalar_one_or_none()
    if not role:
        raise ValueError(
            f"Role '{payload.role}' not found."
        )
    
    # Create membership for the new user in the tenant
    membership = Membership(
        user_id=new_user.id,
        tenant_id=tenant_id,
        role_id=role.id,
        is_active=True,
    )
    db.add(membership)
    
    # Commit Transaction
    try:
        await db.commit()

    except IntegrityError:
        await db.rollback()
        raise

    return UserListItem(
        id=new_user.id,
        email=new_user.email,
        username=new_user.username,
        phone_number=new_user.phone_number,
        is_active=new_user.is_active,
        is_verified=new_user.is_verified,
        role=membership.role.name,
    )
    
async def get_user_detail(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
) -> UserDetail | None:

    result = await db.execute(
        select(User)
        .join(Membership)
        .where(
            User.id == user_id,
            Membership.tenant_id == tenant_id,
        )
        .options(
            selectinload(User.memberships)
            .selectinload(Membership.tenant),

            selectinload(User.memberships)
            .selectinload(Membership.role)
            .selectinload(Role.permissions)
            .selectinload(RolePermission.permission),
        )
    )

    user = result.scalar_one_or_none()

    if not user:
        return None

    memberships = []
    permissions = set()

    for membership in user.memberships:

        memberships.append(
            MembershipSummary(
                tenant=TenantSummary(
                    id=membership.tenant.id,
                    name=membership.tenant.name,
                    slug=membership.tenant.slug,
                ),
                role=membership.role.name,
                is_active=membership.is_active,
            )
        )

        for role_permission in membership.role.permissions:
            permissions.add(
                role_permission.permission.name
            )

    return UserDetail(
        id=user.id,
        email=user.email,
        username=user.username,
        phone_number=user.phone_number,
        is_active=user.is_active,
        is_verified=user.is_verified,
        memberships=memberships,
        permissions=sorted(list(permissions)),
    )
    
async def update_tenant_user(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    payload: UserUpdate,
) -> UserListItem:

    result = await db.execute(
        tenant_user_query(tenant_id)
        .where(User.id == user_id)
    )

    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    # Partial update
    update_data = payload.model_dump(exclude_unset=True)

    # Role handled separately
    role_name = update_data.pop("role", None)

    for field, value in update_data.items():
        if field == "email":
            value = value.lower()

        setattr(user, field, value)

    # Update membership role
    if role_name:
        membership = next(
            (
                membership
                for membership in user.memberships
                if membership.tenant_id == tenant_id
            ),
            None,
        )

        if not membership:
            raise HTTPException(
                status_code=404,
                detail="Membership not found",
            )

        role_result = await db.execute(
            select(Role).where(
                Role.name == role_name,
                Role.tenant_id.is_(None),
            )
        )

        role = role_result.scalar_one_or_none()

        if not role:
            raise HTTPException(
                status_code=404,
                detail="Role not found",
            )

        membership.role_id = role.id

    try:
        await db.commit()
        await db.refresh(user)
        await db.refresh(membership)

    except Exception:
        await db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to update user",
        )

    membership = next(
        (
            membership
            for membership in user.memberships
            if membership.tenant_id == tenant_id
        ),
        None,
    )

    return UserListItem(
        id=user.id,
        email=user.email,
        username=user.username,
        phone_number=user.phone_number,
        is_active=user.is_active,
        is_verified=user.is_verified,
        role=membership.role.name if membership else None,
    )
    
async def get_role_by_name(
    db: AsyncSession,
    role_name: str,
) -> Role | None:
    """Fetch a role by its name. Only global roles (tenant_id is None) are considered."""
    result = await db.execute(
        select(Role).where(
            Role.name == role_name,
            Role.tenant_id.is_(None),
        )
    )
    return result.scalar_one_or_none()

async def get_tenant_doctors(
    db: AsyncSession,
    tenant_id: UUID,
) -> list[UserListItem]:

    doctor_role_result = await db.execute(
        select(Role).where(
            Role.name == "doctor",
            Role.tenant_id.is_(None),
        )
    )

    doctor_role = doctor_role_result.scalar_one_or_none()

    if not doctor_role:
        return []

    result = await db.execute(
        tenant_user_query(tenant_id)
        .where(Membership.role_id == doctor_role.id)
    )

    users = result.scalars().unique().all()

    response: list[UserListItem] = []

    for user in users:
        membership = next(
            (
                membership
                for membership in user.memberships
                if membership.tenant_id == tenant_id
            ),
            None,
        )

        if not membership:
            continue

        response.append(
            UserListItem(
                id=user.id,
                email=user.email,
                username=user.username,
                phone_number=user.phone_number,
                is_active=user.is_active,
                is_verified=user.is_verified,
                role=membership.role.name,
            )
        )

    return response