from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.api.v1.auth.schemas import (
    Register,
    RegisterTenantResponse,
)
from app.api.v1.auth.service import register_tenant_service

from app.core.database import get_db


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post(
    "/register-tenant",
    response_model=RegisterTenantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_tenant(
    payload: Register,
    db: Annotated[AsyncSession, Depends(get_db)],
):

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