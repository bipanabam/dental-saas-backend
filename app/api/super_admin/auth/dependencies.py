import uuid

from typing import Annotated
from fastapi import Depends, status, HTTPException

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import verify_access_token, oauth2_scheme

from app.models.user import (
    Membership,
    User,
)

from dataclasses import dataclass

@dataclass
class SuperAdminAuth:
    user: User

async def get_super_admin(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> SuperAdminAuth:

    payload = verify_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user_id = payload.get("sub")

    result = await db.execute(
        select(User)
        .options(
            selectinload(User.memberships)
            .selectinload(Membership.role)
        )
        .where(User.id == user_id)
    )

    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    is_super_admin = any(
        membership.is_active
        and membership.role.name == "superadmin"
        for membership in user.memberships
    )

    if not is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You aren't authorized to perform this action",
        )

    return SuperAdminAuth(user=user)


CurrentSuperAdmin = Annotated[
    SuperAdminAuth,
    Depends(get_super_admin),
]