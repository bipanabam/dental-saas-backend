"""
Encounter router: all clinical work between start and complete appointment.
"""
from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies.auth import CurrentAuth
from app.models.user import User
from app.schemas.encounter import (
    EncounterUpdate,
    EncounterOut,
    EncounterDetail,
    MedicalHistoryCreate,
    MedicalHistoryOut,
    ExaminationCreate,
    ExaminationEntryOut,
    ClinicalFindingsBulkCreate,
    ClinicalFindingOut,
    DiagnosisBulkCreate,
    DiagnosisOut,
    InvestigationsBulkCreate,
    InvestigationOut,
    InvestigationResultUpdate,
    TreatmentPlanCreate,
    TreatmentPlanOut,
    TreatmentPlanItemPerformCreate,
)
from app.services.encounter import EncounterService
from app.services.medical_history import MedicalHistoryService
from app.services.clinical_examination import ExaminationService
from app.services.clinical_findings import FindingService
from app.services.diagnosis import DiagnosisService
from app.services.investigation import InvestigationService
from app.services.treatmentplan import TreatmentPlanService


router = APIRouter(prefix="/encounters", tags=["Clinical Encounter (Working)"])


@router.get(
    "/by-appointment/{appointment_id}",
    response_model=EncounterDetail,
    summary="Get full encounter for an appointment",
)
async def get_encounter_by_appointment(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    appointment_id: UUID,
    # _: None = CanUpdateAppointments,
):
    """Returns the full clinical encounter with all nested data."""
    return await EncounterService.get_encounter_by_appointment(
        db=db,
        tenant_id=auth.membership.tenant_id,
        appointment_id=appointment_id,
    )


@router.get(
    "/{encounter_id}",
    response_model=EncounterDetail,
    summary="Get encounter by ID",
)
async def get_encounter(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    encounter_id: UUID,
):
    return await EncounterService.get_encounter_by_id(
        db=db,
        tenant_id=auth.membership.tenant_id,
        encounter_id=encounter_id,
    )


@router.patch(
    "/{encounter_id}",
    response_model=EncounterOut,
    summary="Update vitals / chief complaint",
)
async def update_encounter(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    encounter_id: UUID,
    payload: EncounterUpdate,
):
    """Update vitals and chief complaint on an in-progress encounter."""
    return await EncounterService.update_encounter(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.membership.user_id,
        encounter_id=encounter_id,
        payload=payload,
    )


## MEDICAL HISTORY ##
@router.post(
    "/{encounter_id}/history",
    response_model=MedicalHistoryOut,
    status_code=status.HTTP_200_OK,
    summary="Upsert medical history snapshot for this encounter",
)
async def upsert_medical_history(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    encounter_id: UUID,
    payload: MedicalHistoryCreate,
):
    """
    Create or fully replace the medical history for this encounter.
    Sending again overwrites the previous medical-history snapshot.
    item_id values come from MEDICAL_HISTORY_TAXONOMY (frontend static file).
    """
    return await MedicalHistoryService.upsert_medical_history(
        db=db,
        tenant_id=auth.membership.tenant_id,
        encounter_id=encounter_id,
        payload=payload,
    )


@router.get(
    "/{encounter_id}/history",
    response_model=MedicalHistoryOut,
    summary="Get medical history snapshot",
)
async def get_medical_history(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    encounter_id: UUID,
):
    return await MedicalHistoryService.get_medical_history_by_encounter_id(
        db=db,
        tenant_id=auth.membership.tenant_id,
        encounter_id=encounter_id,
    )


## CLINICAL EXAMINATION ##
@router.post(
    "/{encounter_id}/examination",
    response_model=list[ExaminationEntryOut],
    status_code=status.HTTP_200_OK,
    summary="Upsert clinical examination entries",
)
async def upsert_examination(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    encounter_id: UUID,
    payload: ExaminationCreate,
):
    """
    Batch upsert examination form entries.
    field_id values come from ON_EXAMINATION_TAXONOMY (frontend static file).
    Sending again updates only the fields included — partial updates are fine.
    """
    return await ExaminationService.upsert_examination(
        db=db,
        tenant_id=auth.membership.tenant_id,
        encounter_id=encounter_id,
        payload=payload,
    )


@router.get(
    "/{encounter_id}/examination",
    response_model=list[ExaminationEntryOut],
    summary="Get all examination entries",
)
async def get_examination(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    encounter_id: UUID,
):
    return await ExaminationService.get_examination_by_encounter_id(
        db=db,
        tenant_id=auth.membership.tenant_id,
        encounter_id=encounter_id,
    )


## CLINICAL FINDINGS ##
@router.post(
    "/{encounter_id}/findings",
    response_model=list[ClinicalFindingOut],
    status_code=status.HTTP_201_CREATED,
    summary="Add clinical findings",
)
async def create_findings(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    encounter_id: UUID,
    payload: ClinicalFindingsBulkCreate,
):
    """
    Add one or more problems/findings to this encounter.
    finding_code values come from DENTAL_PROBLEM_TAXONOMY.
    Can be called multiple times — each call appends new findings.
    """
    return await FindingService.create_findings(
        db=db,
        tenant_id=auth.membership.tenant_id,
        encounter_id=encounter_id,
        payload=payload,
    )

@router.get(
    "/{encounter_id}/findings",
    response_model=list[ClinicalFindingOut],
    summary="List findings for encounter",
)
async def list_findings(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    encounter_id: UUID,
):
    return await FindingService.get_findings_by_encounter_id(
        db=db,
        tenant_id=auth.membership.tenant_id,
        encounter_id=encounter_id,
    )


@router.delete(
    "/{encounter_id}/findings/{finding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a finding",
)
async def delete_finding(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    encounter_id: UUID,
    finding_id: UUID,
):
    await FindingService.delete_finding(
        db=db,
        tenant_id=auth.membership.tenant_id,
        encounter_id=encounter_id,
        finding_id=finding_id,
    )


## DIAGNOSES ##
@router.post(
    "/{encounter_id}/diagnoses",
    response_model=list[DiagnosisOut],
    status_code=status.HTTP_200_OK,
    summary="Set diagnoses for this encounter",
)
async def create_diagnoses(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    encounter_id: UUID,
    payload: DiagnosisBulkCreate,
):
    """
    Replace all diagnoses for this encounter.
    Exactly one must have is_primary=True (enforced in schema).
    diagnosis_code values come from DENTAL_DIAGNOSIS_TAXONOMY.

    Only DOCTOR role can set diagnoses.
    """
    return await DiagnosisService.replace_diagnoses(
        db=db,
        tenant_id=auth.membership.tenant_id,
        encounter_id=encounter_id,
        payload=payload,
    )


@router.get(
    "/{encounter_id}/diagnoses",
    response_model=list[DiagnosisOut],
    summary="Get diagnoses",
)
async def list_diagnoses(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    encounter_id: UUID,
):
    return await DiagnosisService.get_diagnoses(
        db=db,
        tenant_id=auth.membership.tenant_id,
        encounter_id=encounter_id,
    )


## INVESTIGATIONS ##
@router.post(
    "/{encounter_id}/investigations",
    response_model=list[InvestigationOut],
    status_code=status.HTTP_201_CREATED,
    summary="Order investigations",
)
async def create_investigations(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    encounter_id: UUID,
    payload: InvestigationsBulkCreate,
):
    """
    Order one or more investigations for this visit.
    investigation_code values come from DENTAL_INVESTIGATION_TAXONOMY.
    """
    return await InvestigationService.create_investigations(
        db=db,
        tenant_id=auth.membership.tenant_id,
        encounter_id=encounter_id,
        payload=payload,
    )


@router.get(
    "/{encounter_id}/investigations",
    response_model=list[InvestigationOut],
    summary="List investigations ordered this visit",
)
async def list_investigations(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    encounter_id: UUID,
):
    return await InvestigationService.get_investigations(
        db=db,
        tenant_id=auth.membership.tenant_id,
        encounter_id=encounter_id,
    )


@router.patch(
    "/{encounter_id}/investigations/{investigation_id}/result",
    response_model=InvestigationOut,
    summary="Record investigation result",
)
async def update_investigation_result(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    encounter_id: UUID,
    investigation_id: UUID,
    payload: InvestigationResultUpdate,
):
    """
    Fill in the result after an X-ray or lab result is available.
    Status must be COMPLETED or CANCELLED.
    """
    return await InvestigationService.update_investigation_result(
        db=db,
        tenant_id=auth.membership.tenant_id,
        encounter_id=encounter_id,
        investigation_id=investigation_id,
        payload=payload,
    )


## TREATMENT PLAN ##
@router.post(
    "/{encounter_id}/treatment-plan",
    response_model=TreatmentPlanOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create treatment plan with items",
)
async def create_treatment_plan(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    encounter_id: UUID,
    payload: TreatmentPlanCreate,
):
    """
    Create a treatment plan for this encounter.
    Each item maps to a ProcedureCatalog entry.
    visit_number groups items into future sessions.

    409 if a plan already exists — update via PATCH instead.
    Only DOCTOR role can create treatment plans.
    """
    encounter = await EncounterService._get_encounter_or_404(
        db, auth.membership.tenant_id, encounter_id
    )
    return await EncounterService.create_treatment_plan(
        db=db,
        tenant_id=auth.membership.tenant_id,
        patient_id=encounter.patient_id,
        encounter_id=encounter_id,
        payload=payload,
    )


@router.get(
    "/{encounter_id}/treatment-plan",
    response_model=TreatmentPlanOut,
    summary="Get treatment plan",
)
async def get_treatment_plan(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    encounter_id: UUID,
):
    return await EncounterService.get_treatment_plan(
        db=db,
        tenant_id=auth.membership.tenant_id,
        encounter_id=encounter_id,
    )


@router.post(
    "/{encounter_id}/treatment-plan/items/{item_id}/perform",
    response_model=TreatmentPlanOut,
    status_code=status.HTTP_200_OK,
    summary="Perform a treatment plan item — creates a Procedure",
)
async def perform_treatment_plan_item(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    encounter_id: UUID,
    item_id: UUID,
    payload: TreatmentPlanItemPerformCreate,
):
    """
    Doctor decides to perform a plan item NOW.

    This is the critical transition point:
      TreatmentPlanItem (PENDING) → Procedure (COMPLETED)
      TreatmentPlanItem.status → DONE
      TreatmentPlanItem.performed_procedure_id → new Procedure.id

    Returns the updated treatment plan with the item marked DONE.
    Only DOCTOR role can perform procedures.
    """
    return await EncounterService.perform_treatment_plan_item(
        db=db,
        tenant_id=auth.membership.tenant_id,
        encounter_id=encounter_id,
        item_id=item_id,
        performed_by_id=auth.user.id,
        payload=payload,
    )


@router.patch(
    "/{encounter_id}/treatment-plan/items/{item_id}/defer",
    response_model=TreatmentPlanOut,
    summary="Defer a plan item to a future visit",
)
async def defer_treatment_plan_item(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    encounter_id: UUID,
    item_id: UUID,
):
    """Mark an item as DEFERRED — will not be done today."""
    return await EncounterService.defer_treatment_plan_item(
        db=db,
        tenant_id=auth.membership.tenant_id,
        encounter_id=encounter_id,
        item_id=item_id,
    )