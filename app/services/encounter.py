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
    MedicalHistoryCreate,
    ExaminationCreate,
    ClinicalFindingsBulkCreate,
    DiagnosisBulkCreate,
    InvestigationsBulkCreate,
    InvestigationResultUpdate,
    TreatmentPlanCreate,
    TreatmentPlanItemPerformCreate,
    EncounterOut,
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


class EncounterService:

    # ─── INTERNAL HELPERS ───────────────────────────────────

    @staticmethod
    async def _get_encounter_or_404(
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

    # ─── ENCOUNTER LIFECYCLE ────────────────────────────────

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

    # ─── MEDICAL HISTORY ────────────────────────────────────

    @staticmethod
    async def upsert_medical_history(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        encounter_id: uuid.UUID,
        payload: MedicalHistoryCreate,
    ) -> MedicalHistoryOut:
        encounter = await EncounterService._get_encounter_or_404(
            db, tenant_id, encounter_id
        )

        if encounter.medical_history:
            # Update existing
            history = encounter.medical_history
            history.items = [i.model_dump() for i in payload.items]
            for field in [
                "is_diabetic", "has_hypertension", "has_heart_condition",
                "has_medication_allergy", "is_on_blood_thinners",
                "has_hepatitis_tb", "is_pregnant", "smokes_or_drinks",
            ]:
                val = getattr(payload, field, None)
                if val is not None:
                    setattr(history, field, val)
        else:
            history = EncounterMedicalHistory(
                encounter_id=encounter_id,
                items=[i.model_dump() for i in payload.items],
                **{
                    k: v for k, v in payload.model_dump(exclude={"items"}).items()
                    if v is not None
                },
            )
            db.add(history)

        try:
            await db.commit()
            await db.refresh(history)
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(500, "Failed to save medical history")

        return MedicalHistoryOut.model_validate(history)

    # ─── EXAMINATION ────────────────────────────────────────

    @staticmethod
    async def upsert_examination(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        encounter_id: uuid.UUID,
        payload: ExaminationCreate,
    ) -> list:
        encounter = await EncounterService._get_encounter_or_404(
            db, tenant_id, encounter_id
        )

        # Build a lookup of existing entries by field_id
        existing_map = {e.field_id: e for e in encounter.examination_findings}

        for entry_data in payload.entries:
            if entry_data.field_id in existing_map:
                existing_map[entry_data.field_id].value = entry_data.value
                existing_map[entry_data.field_id].category = entry_data.category
            else:
                db.add(ClinicalExaminationEntry(
                    encounter_id=encounter_id,
                    category=entry_data.category,
                    field_id=entry_data.field_id,
                    value=entry_data.value,
                ))

        try:
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(500, "Failed to save examination")

        await db.refresh(encounter)
        return encounter.examination_findings

    # ─── FINDINGS ───────────────────────────────────────────

    @staticmethod
    async def create_findings(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        encounter_id: uuid.UUID,
        payload: ClinicalFindingsBulkCreate,
    ) -> list:
        await EncounterService._get_encounter_or_404(
            db, tenant_id, encounter_id
        )

        findings = [
            ClinicalFinding(
                encounter_id=encounter_id,
                **f.model_dump(),
            )
            for f in payload.findings
        ]
        db.add_all(findings)

        try:
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(500, "Failed to save findings")

        for f in findings:
            await db.refresh(f)
        return findings

    @staticmethod
    async def delete_finding(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        encounter_id: uuid.UUID,
        finding_id: uuid.UUID,
    ) -> None:
        await EncounterService._get_encounter_or_404(
            db, tenant_id, encounter_id
        )
        result = await db.execute(
            select(ClinicalFinding).where(
                and_(
                    ClinicalFinding.id == finding_id,
                    ClinicalFinding.encounter_id == encounter_id,
                )
            )
        )
        finding = result.scalar_one_or_none()
        if not finding:
            raise HTTPException(404, "Finding not found")
        await db.delete(finding)
        await db.commit()

    # ─── DIAGNOSES ──────────────────────────────────────────

    @staticmethod
    async def create_diagnoses(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        encounter_id: uuid.UUID,
        payload: DiagnosisBulkCreate,
    ) -> list:
        encounter = await EncounterService._get_encounter_or_404(
            db, tenant_id, encounter_id,
            load_full=True,
        )

        # If replacing, clear existing non-primary or all
        # Strategy: clear all and re-insert (simplest for a bulk update)
        for existing in encounter.diagnoses:
            await db.delete(existing)
        await db.flush()

        diagnoses = [
            EncounterDiagnosis(
                encounter_id=encounter_id,
                **d.model_dump(),
            )
            for d in payload.diagnoses
        ]
        db.add_all(diagnoses)

        try:
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(500, "Failed to save diagnoses")

        for d in diagnoses:
            await db.refresh(d)
        return diagnoses

    # ─── INVESTIGATIONS ─────────────────────────────────────

    @staticmethod
    async def create_investigations(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        patient_id: uuid.UUID,
        encounter_id: uuid.UUID,
        payload: InvestigationsBulkCreate,
    ) -> list:
        await EncounterService._get_encounter_or_404(
            db, tenant_id, encounter_id
        )

        investigations = [
            Investigation(
                tenant_id=tenant_id,
                encounter_id=encounter_id,
                patient_id=patient_id,
                **i.model_dump(),
            )
            for i in payload.investigations
        ]
        db.add_all(investigations)

        try:
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(500, "Failed to save investigations")

        for inv in investigations:
            await db.refresh(inv)
        return investigations

    @staticmethod
    async def update_investigation_result(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        encounter_id: uuid.UUID,
        investigation_id: uuid.UUID,
        payload: InvestigationResultUpdate,
    ) -> InvestigationOut:
        result = await db.execute(
            select(Investigation).where(
                and_(
                    Investigation.id == investigation_id,
                    Investigation.encounter_id == encounter_id,
                    Investigation.tenant_id == tenant_id,
                )
            )
        )
        inv = result.scalar_one_or_none()
        if not inv:
            raise HTTPException(404, "Investigation not found")

        inv.result = payload.result
        inv.result_file_url = payload.result_file_url
        inv.status = InvestigationStatusEnum(payload.status)
        if payload.status == "COMPLETED":
            inv.completed_at = datetime.now(UTC)

        try:
            await db.commit()
            await db.refresh(inv)
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(500, "Failed to update investigation")

        return InvestigationOut.model_validate(inv)

    # ─── TREATMENT PLAN ─────────────────────────────────────

    @staticmethod
    async def create_treatment_plan(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        patient_id: uuid.UUID,
        encounter_id: uuid.UUID,
        payload: TreatmentPlanCreate,
    ) -> TreatmentPlanOut:
        encounter = await EncounterService._get_encounter_or_404(
            db, tenant_id, encounter_id
        )

        if encounter.treatment_plan:
            raise HTTPException(
                409,
                "A treatment plan already exists for this encounter. "
                "Use PATCH /encounters/{id}/treatment-plan to update it.",
            )

        estimated_total = sum(
            item.estimated_cost or 0.0
            for item in payload.items
        )

        plan = TreatmentPlan(
            tenant_id=tenant_id,
            encounter_id=encounter_id,
            patient_id=patient_id,
            notes=payload.notes,
            estimated_total_cost=estimated_total,
        )
        db.add(plan)
        await db.flush()

        items = [
            TreatmentPlanItem(
                treatment_plan_id=plan.id,
                **item.model_dump(),
            )
            for item in payload.items
        ]
        db.add_all(items)

        try:
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(500, "Failed to create treatment plan")

        await db.refresh(plan)
        return TreatmentPlanOut.model_validate(plan)

    @staticmethod
    async def perform_treatment_plan_item(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        encounter_id: uuid.UUID,
        item_id: uuid.UUID,
        performed_by_id: uuid.UUID,
        payload: TreatmentPlanItemPerformCreate,
    ) -> TreatmentPlanOut:
        """
        Doctor decides to perform a plan item NOW.
        Creates a Procedure row, marks item as DONE.
        """
        result = await db.execute(
            select(TreatmentPlanItem)
            .join(TreatmentPlan)
            .where(
                and_(
                    TreatmentPlanItem.id == item_id,
                    TreatmentPlan.encounter_id == encounter_id,
                    TreatmentPlan.tenant_id == tenant_id,
                )
            )
            .options(
                selectinload(TreatmentPlanItem.procedure_catalog),
                selectinload(TreatmentPlanItem.treatment_plan),
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(404, "Treatment plan item not found")

        if item.status == TreatmentPlanItemStatusEnum.DONE:
            raise HTTPException(409, "This item has already been performed")

        # Get encounter for patient_id + appointment_id
        encounter = await EncounterService._get_encounter_or_404(
            db, tenant_id, encounter_id
        )

        # Create actual Procedure
        procedure = Procedure(
            tenant_id=tenant_id,
            patient_id=encounter.patient_id,
            appointment_id=encounter.appointment_id,
            encounter_id=encounter_id,
            procedure_catalog_id=item.procedure_catalog_id,
            tooth_numbers=item.tooth_numbers,
            status=ProcedureStatusEnum.COMPLETED,
            final_cost=payload.final_cost or item.estimated_cost,
            estimated_cost=item.estimated_cost,
            performed_by_id=performed_by_id,
            performed_duration_minutes=payload.performed_duration_minutes,
            procedure_date=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        db.add(procedure)
        await db.flush()

        # Mark plan item as DONE and link to procedure
        item.status = TreatmentPlanItemStatusEnum.DONE
        item.performed_procedure_id = procedure.id

        try:
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(500, "Failed to perform treatment plan item")

        await db.refresh(item.treatment_plan)
        return TreatmentPlanOut.model_validate(item.treatment_plan)