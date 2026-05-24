from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies.auth import CurrentAuth
from app.core.dependencies.permissions import CanReadUsers, CanCreateUsers, CanUpdateUsers, CanDeleteUsers

from app.api.v1.users.services import (
    get_tenant_users, 
    create_tenant_user, 
    get_user_detail,
    update_tenant_user
)
from app.models.user import Membership, Role, User
from app.schemas.users import (
    UserListItem, 
    UserCreate, 
    UserDetail,
    UserUpdate,
)


router = APIRouter(
    prefix="/users", 
    tags=["users"]
)

# GET -> /users
@router.get("/")
async def get_users(
    auth: CurrentAuth,
     db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanReadUsers,
):
    """Get a list of users in the current tenant"""
    users =  await get_tenant_users(
        db,
        auth.membership.tenant_id,
    )
    return {
        "count": len(users),
        "users": users
    }
    
# POST -> /users
@router.post("/", response_model=UserListItem)
async def create_user(
    payload: UserCreate,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanCreateUsers,
) -> UserListItem:
    """Create a new user in the current tenant"""
    new_user = await create_tenant_user(
        db,
        payload,
        tenant_id=auth.membership.tenant_id
    )

    return new_user

# GET -> /users/{user_id}
@router.get(
    "/{user_id}",
    response_model=UserDetail,
)
async def get_user(
    user_id: UUID,
    auth: CurrentAuth,
    db: AsyncSession = Depends(get_db),
    _: None = CanReadUsers,
):

    user = await get_user_detail(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=user_id,
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return user

# PUT -> /users/{user_id}
@router.put("/{user_id}")
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    auth: CurrentAuth,
    db: AsyncSession = Depends(get_db),
    _: None = CanUpdateUsers,
) -> UserListItem:
    """Update user details"""
    updated_user = await update_tenant_user(
        db,
        tenant_id=auth.membership.tenant_id,
        user_id=user_id,
        payload=payload,
    )

    return updated_user
    

# DELETE -> /users/{user_id}
@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    auth: CurrentAuth,
    db: AsyncSession = Depends(get_db),
    _: None = CanDeleteUsers,
):
    """
    Soft delete user from tenant.
    """

    result = await db.execute(
        select(Membership)
        .options(
            selectinload(Membership.user)
        )
        .where(
            Membership.user_id == user_id,
            Membership.tenant_id == auth.membership.tenant_id,
        )
    )

    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    membership.is_active = False
    membership.user.is_active = False

    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Cannot delete user with related records",
        )

    return {"detail": "User deleted successfully"}