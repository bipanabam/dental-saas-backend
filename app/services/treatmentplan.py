from uuid import UUID
from datetime import datetime, UTC

from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models import TreatmentPlan, TreatmentPlanItem, Procedure
from app.utils.enums import TreatmentPlanItemStatusEnum, ProcedureStatusEnum

from app.services.encounter import EncounterRepository

from app.schemas.encounter import (
    TreatmentPlanCreate, 
    TreatmentPlanOut,
    TreatmentPlanItemPerformCreate
)

class TreatmentPlanRepository:

    @staticmethod
    async def get_by_encounter(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
    ) -> TreatmentPlan:

        result = await db.execute(
            select(TreatmentPlan)
            .where(
                and_(
                    TreatmentPlan.tenant_id == tenant_id,
                    TreatmentPlan.encounter_id == encounter_id,
                )
            )
            .options(
                selectinload(TreatmentPlan.items)
                .selectinload(
                    TreatmentPlanItem.procedure_catalog
                )
            )
        )

        plan = result.scalar_one_or_none()

        if not plan:
            raise HTTPException(
                404,
                "Treatment plan not found",
            )

        return plan

class TreatmentPlanService:

    @staticmethod
    async def create_treatment_plan(
        db: AsyncSession,
        tenant_id: UUID,
        patient_id: UUID,
        encounter_id: UUID,
        payload: TreatmentPlanCreate,
    ) -> TreatmentPlanOut:
        encounter = await EncounterRepository._get_or_404(
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


class TreatmentPlanExecutionService:

    @staticmethod
    async def perform_treatment_plan_item(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
        item_id: UUID,
        performed_by_id: UUID,
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
        encounter = await EncounterRepository._get_or_404(
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

    async def defer_item():
        pass

    async def cancel_item():
        pass    