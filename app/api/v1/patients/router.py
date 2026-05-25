from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies.auth import CurrentAuth
from app.schemas.patient import PatientCreate, PatientResponse
from app.core.database import AsyncSession, get_db  

from app.api.v1.patients.services import PatientService


router = APIRouter(
    prefix="/patients",
    tags=["patients"],
)

@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    payload: PatientCreate,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PatientResponse:
    """Create a new patient for the tenant"""

    return await PatientService.create_patient(
        db=db,
        tenant_id=auth.membership.tenant_id,
        tenant_name=auth.membership.tenant.name,
        user_id=auth.user.id,
        payload=payload
    )