from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies.auth import CurrentAuth
from app.core.dependencies.permissions import CanCreatePatients, CanReadPatients
from app.schemas.patient import PatientCreate, PatientResponse, PatientListItem, PatientDetail, PatientUpdate
from app.core.database import AsyncSession, get_db  

from app.api.v1.patients.services import PatientService
from app.utils.enums import PatientCategoryEnum, PatientStatusEnum, GenderEnum, BloodGroupEnum


router = APIRouter(
    prefix="/patients",
    tags=["patients"],
)

# POST -> /patients
@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    payload: PatientCreate,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanCreatePatients,
) -> PatientResponse:
    """Create a new patient for the tenant"""

    return await PatientService.create_patient(
        db=db,
        tenant_id=auth.membership.tenant_id,
        tenant_name=auth.membership.tenant.name,
        user_id=auth.user.id,
        payload=payload
    )
    
# GET -> /patients
@router.get("/", response_model=list[PatientListItem])
async def list_patients(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    category: PatientCategoryEnum | None = None,
    status: PatientStatusEnum | None = None,
    gender: GenderEnum | None = None,
    blood_group: BloodGroupEnum | None = None,
    _: None = CanReadPatients,
) -> list[PatientListItem]:
    """List all patients for the tenant"""

    result =  await PatientService.list_patients(
        db=db,
        tenant_id=auth.membership.tenant_id,
        category=category,
        status=status,
        gender=gender,
        blood_group=blood_group
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No patients found for this tenant"
        )
        
    return result

# GET -> /patients/search
@router.get("/search", response_model=list[PatientListItem])
async def search_patients(
    query: str,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanReadPatients,
) -> list[PatientListItem]:
    """Search patients by name, code, phone, or email"""

    result = await PatientService.search_patients(
        db=db,
        tenant_id=auth.membership.tenant_id,
        query=query
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No patients found for this tenant"
        )

    return result

# GET -> /patients/{patient_id}
@router.get("/{patient_id}", response_model=PatientDetail)
async def get_patient(
    patient_id: UUID,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanReadPatients,
) -> PatientDetail:
    """Get a specific patient by ID"""

    return await PatientService.get_patient_by_id(
        db=db,
        tenant_id=auth.membership.tenant_id,
        patient_id=patient_id
    )

# PUT -> /patients/{patient_id}
@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: UUID,
    payload: PatientUpdate,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanCreatePatients,
):
    """Update a specific patient by ID"""

    return await PatientService.update_patient(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.user.id,
        patient_id=patient_id,
        payload=payload.dict(exclude_unset=True)
    )
    
# DELETE -> /patients/{patient_id}
@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: UUID,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanCreatePatients,
):
    """Delete a specific patient by ID"""

    await PatientService.delete_patient(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.user.id,
        patient_id=patient_id
    )