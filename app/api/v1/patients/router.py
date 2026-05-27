from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies.auth import CurrentAuth
from app.core.dependencies.permissions import CanCreatePatients, CanReadPatients
from app.schemas.patient import (
    FamilyLinkCreate, 
    FamilyListItem,
    MedicalRecordPayload, 
    PatientCreate, 
    PatientResponse, 
    PatientListItem, 
    PatientDetail, 
    PatientUpdate,
    MedicalRecordSummary
)
from app.core.database import AsyncSession, get_db  

from app.api.v1.patients.services import PatientService
from app.utils.enums import PatientCategoryEnum, PatientStatusEnum, GenderEnum, BloodGroupEnum


router = APIRouter(
    prefix="/patients",
    tags=["patients"],
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

# POST -> /patients/check-duplicate
@router.post("/check-duplicate", response_model=bool)
async def check_duplicate_patient(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    phone: str | None = None,
    email: str | None = None,
    _: None = CanCreatePatients,
) -> bool:
    """Check if a patient with the same name, code, phone, or email already exists for the tenant"""
    if not phone and not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of phone or email must be provided"
        )

    return await PatientService.check_duplicate_patient(
        db=db,
        tenant_id=auth.membership.tenant_id,
        email=email,
        phone=phone
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
    
# GET -> /{patient_id}/medical-record
@router.get("/{patient_id}/medical-record", response_model=MedicalRecordSummary)
async def get_medical_record(
    patient_id: UUID,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanReadPatients,
) -> MedicalRecordSummary:
    """Get the medical record summary for a specific patient"""

    result = await PatientService.get_medical_record_summary(
        db=db,
        tenant_id=auth.membership.tenant_id,
        patient_id=patient_id
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical record not found for this patient"
        )

    return result   

# POST -> /{patient_id}/medical-record
@router.post("/{patient_id}/medical-record", response_model=MedicalRecordSummary)
async def create_or_update_medical_record(
    patient_id: UUID,
    payload: MedicalRecordPayload,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanCreatePatients,
) -> MedicalRecordSummary:
    """Create or update the medical record for a specific patient"""
    if not any([payload.allergies, payload.systemic_conditions, payload.current_medications, payload.prior_surgeries, payload.emergency_contact_name, payload.emergency_contact_phone]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one medical record field must be provided"
        )

    return await PatientService.create_or_update_medical_record(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.user.id,
        patient_id=patient_id,
        payload=payload
    )
    
# POST -> /{patient_id}/assign-doctor
@router.post("/{patient_id}/assign-doctor", response_model=MedicalRecordSummary)
async def assign_primary_doctor(
    patient_id: UUID,
    doctor_id: UUID,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanCreatePatients,
) -> MedicalRecordSummary:
    """Assign or change the primary doctor for a specific patient"""

    return await PatientService.assign_primary_doctor(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.user.id,
        patient_id=patient_id,
        doctor_id=doctor_id
    )
    
# GET -> /{patient_id}/family
@router.get("/{patient_id}/family", response_model=list[FamilyListItem])
async def list_family_members(
    patient_id: UUID,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanReadPatients,
) -> list[FamilyListItem]:
    """List all linked family members of a specific patient"""

    result = await PatientService.list_family_members(
        db=db,
        tenant_id=auth.membership.tenant_id,
        primary_account_id=patient_id
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No family members found for this patient"
        )

    return result

# POST -> /{patient_id}/family
@router.post("/{patient_id}/family", response_model=FamilyListItem, status_code=status.HTTP_201_CREATED)
async def add_family_member(
    patient_id: UUID,
    payload: FamilyLinkCreate,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanCreatePatients,
) -> FamilyListItem:
    """Link a family member to a specific patient"""

    return await PatientService.add_family_member(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.user.id,
        primary_account_id=patient_id,
        payload=payload
    )
    
# DELETE -> /{patient_id}/family/{family_member_id}
@router.delete("/{patient_id}/family/{family_member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_family_member( 
    patient_id: UUID,
    family_member_id: UUID,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanCreatePatients,
):
    """Unlink a family member from a specific patient"""

    return await PatientService.remove_family_member(
        db=db,
        tenant_id=auth.membership.tenant_id,
        primary_account_id=patient_id,
        family_member_id=family_member_id   
        )