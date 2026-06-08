"""
EncounterService — all business logic for the clinical encounter lifecycle.

Called from:
  - AppointmentWorkflowService.start_appointment()   → create_encounter()
  - AppointmentWorkflowService.complete_appointment() → validate_encounter_for_completion()
  - Encounter routers                                 → everything else
"""
from __future__ import annotations
import uuid
from datetime import datetime, UTC

from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.models.encounter import (
    ClinicalEncounter,
    EncounterMedicalHistory,
    ClinicalExaminationEntry,
    ClinicalFinding,
    EncounterDiagnosis,
    Investigation,
    TreatmentPlan,
    TreatmentPlanItem,
)
from app.models.procedure import Procedure
from app.schemas.encounter import (
    EncounterCreate,
    EncounterUpdate,
    EncounterOut,
    MedicalHistoryCreate,
    ExaminationCreate,
    ClinicalFindingsBulkCreate,
    DiagnosisBulkCreate,
    InvestigationsBulkCreate,
    InvestigationResultUpdate,
    TreatmentPlanCreate,
    TreatmentPlanItemPerformCreate,
    EncounterDetail,
    MedicalHistoryOut,
    TreatmentPlanOut,
    InvestigationOut,
)
from app.utils.enums import (
    EncounterStatusEnum,
    TreatmentPlanItemStatusEnum,
    ProcedureStatusEnum,
    InvestigationStatusEnum,
)


class EncounterRepository:
    @staticmethod
    async def _get_or_404(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        encounter_id: uuid.UUID,
        load_full: bool = False,
    ) -> ClinicalEncounter:
        opts = []
        if load_full:
            opts = [
                selectinload(ClinicalEncounter.medical_history),
                selectinload(ClinicalEncounter.examination_findings),
                selectinload(ClinicalEncounter.clinical_findings),
                selectinload(ClinicalEncounter.diagnoses),
                selectinload(ClinicalEncounter.investigations),
                selectinload(ClinicalEncounter.treatment_plan).selectinload(
                    TreatmentPlan.items
                ),
                selectinload(ClinicalEncounter.procedures),
            ]

        result = await db.execute(
            select(ClinicalEncounter)
            .where(
                and_(
                    ClinicalEncounter.id == encounter_id,
                    ClinicalEncounter.tenant_id == tenant_id,
                )
            )
            .options(*opts)
        )
        encounter = result.scalar_one_or_none()
        if not encounter:
            raise HTTPException(404, "Clinical encounter not found")
        return encounter
    
    @staticmethod
    async def ensure_encounter_exists(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        encounter_id: uuid.UUID,
    ) -> None:
        result = await db.execute(
            select(ClinicalEncounter.id).where(
                and_(
                    ClinicalEncounter.id == encounter_id,
                    ClinicalEncounter.tenant_id == tenant_id,
                )
            )
        )

        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=404,
                detail="Clinical encounter not found",
            )
        
class EncounterService:
    
    @staticmethod
    async def _get_encounter_by_appointment_or_404(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        appointment_id: uuid.UUID,
    ) -> ClinicalEncounter:
        result = await db.execute(
            select(ClinicalEncounter).where(
                and_(
                    ClinicalEncounter.appointment_id == appointment_id,
                    ClinicalEncounter.tenant_id == tenant_id,
                )
            )
        )
        encounter = result.scalar_one_or_none()
        if not encounter:
            raise HTTPException(404, "No clinical encounter for this appointment")
        return encounter
    
    @staticmethod
    async def get_encounter_by_appointment(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        appointment_id: uuid.UUID,
    ) -> EncounterDetail:
        result = await db.execute(
            select(ClinicalEncounter)
            .where(
                and_(
                    ClinicalEncounter.appointment_id == appointment_id,
                    ClinicalEncounter.tenant_id == tenant_id,
                )
            )
            .options(
                selectinload(ClinicalEncounter.medical_history),
                selectinload(ClinicalEncounter.examination_findings),
                selectinload(ClinicalEncounter.clinical_findings),
                selectinload(ClinicalEncounter.diagnoses),
                selectinload(ClinicalEncounter.investigations),
                selectinload(ClinicalEncounter.treatment_plan).selectinload(
                    TreatmentPlan.items
                ),
                selectinload(ClinicalEncounter.procedures),
            )
        )
        encounter = result.scalar_one_or_none()
        if not encounter:
            raise HTTPException(404, "No clinical encounter for this appointment")
        return EncounterDetail.model_validate(encounter)
    
    @staticmethod
    async def get_encounter_by_id(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        encounter_id: uuid.UUID,
    ) -> EncounterDetail:
        result = await db.execute(
            select(ClinicalEncounter)
            .where(
                and_(
                    ClinicalEncounter.id == encounter_id,
                    ClinicalEncounter.tenant_id == tenant_id,
                )
            )
            .options(
                selectinload(ClinicalEncounter.medical_history),
                selectinload(ClinicalEncounter.examination_findings),
                selectinload(ClinicalEncounter.clinical_findings),
                selectinload(ClinicalEncounter.diagnoses),
                selectinload(ClinicalEncounter.investigations),
                selectinload(ClinicalEncounter.treatment_plan).selectinload(
                    TreatmentPlan.items
                ),
                selectinload(ClinicalEncounter.procedures),
            )
        )
        encounter = result.scalar_one_or_none()
        if not encounter:
            raise HTTPException(404, "No clinical encounter for this appointment")
        return EncounterDetail.model_validate(encounter)

    # ENCOUNTER LIFECYCLE
    @staticmethod
    async def create_encounter(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        patient_id: uuid.UUID,
        appointment_id: uuid.UUID,
        doctor_id: uuid.UUID | None,
        created_by_id: uuid.UUID,
        payload: EncounterCreate,
    ) -> ClinicalEncounter:
        """
        Called by AppointmentWorkflowService.start_appointment().
        Idempotent — returns existing encounter if one exists.
        """
        # Idempotency: return existing if already created
        existing_result = await db.execute(
            select(ClinicalEncounter).where(
                ClinicalEncounter.appointment_id == appointment_id
            )
        )
        if existing := existing_result.scalar_one_or_none():
            return existing

        encounter = ClinicalEncounter(
            tenant_id=tenant_id,
            appointment_id=appointment_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            created_by_id=created_by_id,
            started_at=datetime.now(UTC),
            status=EncounterStatusEnum.IN_PROGRESS,
            **payload.model_dump(exclude_none=True),
        )
        db.add(encounter)

        try:
            await db.flush()  # get encounter.id without committing
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(500, "Failed to create clinical encounter")

        return encounter
    
    @staticmethod
    async def update_encounter(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        encounter_id: uuid.UUID,
        payload: EncounterUpdate,
    ) -> ClinicalEncounter:
        """
        Updates the clinical encounter details.
        """
        # Idempotency: return existing if already created
        encounter = await EncounterRepository._get_or_404(
            db=db,
            tenant_id=tenant_id,
            encounter_id=encounter_id
        )
        
        if encounter.status == EncounterStatusEnum.CLOSED:
            raise HTTPException(
                status_code=400,
                detail="Completed encounters cannot be modified",
            )
        
        update_data = payload.model_dump(
            exclude_unset=True,
            exclude_none=True,
        )
        for field, value in update_data.items():
            setattr(encounter, field, value)
            
        if hasattr(encounter, "updated_by_id"):
            encounter.updated_by_id = user_id

        try:
            await db.commit()
            await db.refresh(encounter)
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Failed to update clinical encounter",
            )
        return encounter

class EncounterFlowService:
    @staticmethod
    async def start_encounter():
        pass

    @staticmethod
    async def validate_encounter_for_completion(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        appointment_id: uuid.UUID,
    ) -> None:
        """
        Called by complete_appointment() BEFORE marking appointment COMPLETED.
        Raises 400 if clinical requirements are not met.
        """
        result = await db.execute(
            select(ClinicalEncounter)
            .where(
                and_(
                    ClinicalEncounter.appointment_id == appointment_id,
                    ClinicalEncounter.tenant_id == tenant_id,
                )
            )
            .options(selectinload(ClinicalEncounter.diagnoses))
        )
        encounter = result.scalar_one_or_none()

        if not encounter:
            raise HTTPException(
                400,
                "Cannot complete appointment: no clinical encounter was started. "
                "Call POST /appointments/{id}/start first.",
            )

        primary_diagnoses = [d for d in encounter.diagnoses if d.is_primary]
        if not primary_diagnoses:
            raise HTTPException(
                400,
                "Cannot complete appointment: a primary diagnosis is required. "
                "Add at least one diagnosis via POST /encounters/{id}/diagnoses.",
            )
            
    @staticmethod
    async def close_encounter(
        db: AsyncSession,
        encounter: ClinicalEncounter,
    ) -> None:
        """
        Called after appointment.status → COMPLETED.
        Closes the encounter. Does NOT commit — caller commits.
        """
        encounter.status = EncounterStatusEnum.CLOSED
        encounter.closed_at = datetime.now(UTC)

    async def complete_encounter(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        encounter_id: uuid.UUID,
    ):
        encounter = EncounterRepository._get_or_404(
            id=id,
            tenant_id=tenant_id,
            encounter_id=encounter_id
        )
        await EncounterFlowService.validate_encounter_for_completion(
            db=db,
            tenant_id=tenant_id,
            appointment_id=encounter.appointment_id
        )

        encounter.status = EncounterStatusEnum.CLOSED

        # appointment.status = COMPLETED

        # queue.status = COMPLETED

    async def reopen_encounter():
        pass