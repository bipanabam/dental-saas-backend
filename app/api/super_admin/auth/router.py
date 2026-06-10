from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.super_admin.auth.dependencies import CurrentSuperAdmin

from app.api.super_admin.schema import Token

router = APIRouter(prefix="/super-admin/auth", tags=["Super-Admin Auth"])

# GET -> /auth/me
@router.get("/me")
async def me(
    auth: CurrentSuperAdmin, 
):
    return auth.user


# POST -> /auth/login
@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    pass