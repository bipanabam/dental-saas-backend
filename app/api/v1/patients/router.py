from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies.auth import CurrentAuth
from app.core.dependencies.permissions import (
    CanCreatePatients, 
    CanReadPatients,
    CanUpdatePatients,
    CanDeletePatients,
    CanReadAppointments
)
from app.schemas.patient import (
    PatientListItem, 
    PatientFilter,
    PatientListResponse,
    FamilyLinkCreate, 
    FamilyListItem,
    MedicalRecordPayload, 
    PatientCreate, 
    PatientResponse, 
    PatientDetail, 
    PatientUpdate,
    MedicalRecordSummary,
    PatientSummaryResponse
)
from app.schemas.appointment import AppointmentListResponse, AppointmentFilter
from app.core.database import AsyncSession, get_db  

from app.api.v1.patients.services import PatientService


router = APIRouter(
    prefix="/patients",
    tags=["patients"],
)

# GET -> /patients
@router.get("/", response_model=PatientListResponse)
async def list_patients(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    filter: Annotated[
        PatientFilter,
        Depends()
    ],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    _: None = CanReadPatients,
):
    """List all patients for the tenant"""

    result =  await PatientService.list_patients(
        db=db,
        tenant_id=auth.membership.tenant_id,
        filter=filter,
        skip=skip,
        limit=limit
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
    _: None = CanUpdatePatients,
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
    _: None = CanDeletePatients,
):
    """Delete a specific patient by ID"""

    await PatientService.delete_patient(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.user.id,
        patient_id=patient_id
    )
    
# DELETE -> /patients/{patient_id}
@router.put("/{patient_id}/restore")
async def restore_patient(
    patient_id: UUID,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanUpdatePatients,
):
    """
    Restore a soft-deleted patient in the tenant.
    """

    await PatientService.restore_patient(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.user.id,
        patient_id=patient_id
    )
    return {"detail": "Patient restored successfully"}
    

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
    _: None = CanUpdatePatients,
) -> FamilyListItem:
    """Link an existing patient as family member"""

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
    _: None = CanUpdatePatients,
):
    """Unlink a family member from a specific patient"""

    return await PatientService.remove_family_member(
        db=db,
        tenant_id=auth.membership.tenant_id,
        primary_account_id=patient_id,
        family_member_id=family_member_id   
        )
    
# GET -> /{patient_id}/appointments
@router.get(
    "/{patient_id}/appointments",
    response_model=AppointmentListResponse,
)
async def list_patient_appointments(
    patient_id: UUID,
    auth: CurrentAuth,
    db: Annotated[
        AsyncSession,
        Depends(get_db)
    ],
    filter: Annotated[
        AppointmentFilter,
        Depends()
    ],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    _: None = CanReadAppointments,
) -> AppointmentListResponse:
    """List appointments for patient"""

    return await PatientService.get_appointments(
        db=db,
        tenant_id=auth.membership.tenant_id,
        patient_id=patient_id,
        filter=filter,
        skip=skip,
        limit=limit,
    )
    
# GET -> /patients/{patient_id}/summary
@router.get(
    "/{patient_id}/summary",
    response_model=PatientSummaryResponse,
)
async def get_patient_summary(
    patient_id: UUID,
    auth: CurrentAuth,
    db: Annotated[
        AsyncSession,
        Depends(get_db)
    ],
    _: None = CanReadPatients,
):
    """Printable one-page patient summary"""

    return await PatientService.get_patient_summary(
        db=db,
        tenant_id=auth.membership.tenant_id,
        patient_id=patient_id,
    )