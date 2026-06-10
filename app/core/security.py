from datetime import UTC, datetime, timedelta
from typing import Any
import uuid
import hashlib

from fastapi.params import Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordBearer

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_PREFIX}/auth/token"
)

oauth2_refresh_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_PREFIX}/auth/refresh"
)

def hash_password(password: str) -> str:
    """Hash a plaintext password"""
    return str(password_hash.hash(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a hashed password"""
    return bool(password_hash.verify(plain_password, hashed_password))

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def create_access_token(
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    tenant_slug: str,
    role: str,
) -> str:
    """Create a JWT access token with user and tenant information"""

    expire = datetime.now(UTC) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "tenant_slug": tenant_slug,
        "role": role,
        "type": "access",
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )

def create_refresh_token(
    *,
    user_id: uuid.UUID,
) -> str:
    expire = datetime.now(UTC) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )

def verify_access_token(token: str) -> dict[str, Any] | None:
    """Verify a JWT access token and return the data if valid"""
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY.get_secret_value(), 
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        return payload
    except jwt.InvalidTokenError:
        return None 
    
def verify_token(token: str) -> dict[str, Any] | None:
    """Verify a JWT token (access or refresh) and return the data if valid"""
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY.get_secret_value(), 
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        return payload
    except jwt.InvalidTokenError:
        return None