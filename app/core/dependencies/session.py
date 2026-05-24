from typing import Annotated, Any
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.tenant import RefreshIn
from app.core.database import get_db
from app.core.security import (
    hash_token,
    verify_token
)
from app.models.user import UserSession

@dataclass
class RefreshSessionData:
    session: UserSession
    payload: dict[str, Any]


async def get_current_session(
    payload: RefreshIn,
    db: AsyncSession = Depends(get_db),
) -> RefreshSessionData:

    token_data = verify_token(payload.refresh_token)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if token_data.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    token_hash = hash_token(payload.refresh_token)

    result = await db.execute(
        select(UserSession).where(
            UserSession.refresh_token_hash == token_hash,
            UserSession.is_revoked.is_(False),
        )
    )

    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh session revoked",
        )

    if session.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )

    return RefreshSessionData(session=session, payload=token_data)
    
CurrentSession = Annotated[
    RefreshSessionData,
    Depends(get_current_session),
]