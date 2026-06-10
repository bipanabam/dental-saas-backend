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
    TreatmentPlan,
)
from app.models.procedure import Procedure

from app.schemas.encounter import (
    EncounterCreate,
    EncounterUpdate,
    EncounterDetail,
    EncounterOut,
    MedicalHistoryOut,
    ExaminationEntryOut,
    TreatmentPlanOut,
    ProcedureSummary
)
from app.utils.enums import (
    EncounterStatusEnum,
    TreatmentPlanItemStatusEnum,
    InvestigationStatusEnum
)


class EncounterRepository:
    @staticmethod
    async def get_or_404(
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
                
                selectinload(ClinicalEncounter.procedures)
                .selectinload(
                    Procedure.procedure_catalog
                ),
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
    async def get_by_appointment_id(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        appointment_id: uuid.UUID,
    ) -> ClinicalEncounter:
        result = await db.execute(
            select(ClinicalEncounter)
            .where(
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
            
    @staticmethod
    async def get_for_closure(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        encounter_id: uuid.UUID,
    ) -> ClinicalEncounter:

        result = await db.execute(
            select(ClinicalEncounter)
            .where(
                ClinicalEncounter.id == encounter_id,
                ClinicalEncounter.tenant_id == tenant_id,
            )
            .options(
                selectinload(ClinicalEncounter.diagnoses),
                selectinload(ClinicalEncounter.treatment_plan)
                .selectinload(TreatmentPlan.items),
            )
        )

        encounter = result.scalar_one_or_none()

        if not encounter:
            raise HTTPException(
                404,
                "Encounter not found",
            )

        return encounter
                
class EncounterMapper:
    
    @staticmethod
    def to_detail(
        encounter: ClinicalEncounter,
    ) -> EncounterDetail:
        from app.services.clinical_findings import FindingMapper
        from app.services.diagnosis import DiagnosisMapper
        from app.services.investigation import InvestigationMapper
        from app.services.treatmentplan import TreatmentPlanMapper
        from app.services.procedure import ProcedureMapper

        return EncounterDetail(
            **EncounterOut.model_validate(encounter).model_dump(),
            
            medical_history=(
                MedicalHistoryOut.model_validate(encounter.medical_history)
                if encounter.medical_history
                else None
            ),

            examination_findings=[
                ExaminationEntryOut.model_validate(exam)
                for exam in encounter.examination_findings
            ],

            clinical_findings=[
                FindingMapper.to_finding_out(f)
                for f in encounter.clinical_findings
            ],

            diagnoses=[
                DiagnosisMapper.to_diagnosis_out(d)
                for d in encounter.diagnoses
            ],

            investigations=[
                InvestigationMapper.to_investigation_out(inv)
                for inv in encounter.investigations
            ],

            treatment_plan=(
                TreatmentPlanOut.model_validate(encounter.treatment_plan)
                if encounter.treatment_plan
                else None
            ),

            procedures=[
                ProcedureMapper.to_procedure_summary(proc)
                for proc in encounter.procedures
            ],
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
        return EncounterMapper.to_detail(encounter)
    
    @staticmethod
    async def get_encounter_by_id(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        encounter_id: uuid.UUID,
    ) -> EncounterDetail:
        encounter = await EncounterRepository.get_or_404(
            db=db,
            tenant_id=tenant_id,
            encounter_id=encounter_id,
            load_full=True
        )
        if not encounter:
            raise HTTPException(404, "No clinical encounter for this appointment")
        return EncounterMapper.to_detail(encounter)

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
        encounter = await EncounterRepository.get_or_404(
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
    
class EncounterClosureValidator:

    @staticmethod
    def validate(
        encounter: ClinicalEncounter,
    ) -> None:

        if encounter.status != EncounterStatusEnum.IN_PROGRESS:
            raise HTTPException(
                400,
                "Encounter is not active",
            )

        if not encounter.diagnoses:
            raise HTTPException(
                400,
                "At least one diagnosis is required",
            )

        primary_diagnoses = [
            diagnosis
            for diagnosis in encounter.diagnoses
            if diagnosis.is_primary
        ]

        if len(primary_diagnoses) != 1:
            raise HTTPException(
                400,
                "Exactly one primary diagnosis is required",
            )

        if encounter.treatment_plan:
            invalid_items = [
                item
                for item in encounter.treatment_plan.items
                if (
                    item.status
                    == TreatmentPlanItemStatusEnum.DONE
                    and not item.performed_procedure_id
                )
            ]

            if invalid_items:
                raise HTTPException(
                    400,
                    "Completed treatment items must have procedures attached",
                )

class EncounterFlowService:
    @staticmethod
    async def start_encounter():
        pass
    
    @staticmethod
    async def close_encounter(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        encounter_id: uuid.UUID,
    ) -> ClinicalEncounter:

        encounter = (
            await EncounterRepository.get_for_closure(
                db=db,
                tenant_id=tenant_id,
                encounter_id=encounter_id,
            )
        )
        
        if encounter.status == EncounterStatusEnum.CLOSED:
            return encounter

        EncounterClosureValidator.validate(
            encounter
        )
        

        encounter.status = (
            EncounterStatusEnum.CLOSED
        )

        encounter.closed_at = datetime.now(UTC)
        encounter.closed_by_id = user_id
        return encounter

    async def reopen_encounter():
        pass