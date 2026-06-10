from uuid import UUID
from datetime import datetime, UTC

from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models import TreatmentPlan, TreatmentPlanItem, Procedure
from app.utils.enums import TreatmentPlanItemStatusEnum, TreatmentPlanStatusEnum

from app.services.encounter import EncounterRepository
from app.services.procedure import ProcedureFactory

from app.schemas.encounter import (
    TreatmentPlanCreate, 
    TreatmentPlanOut,
    TreatmentPlanItemOut,
    TreatmentPlanItemPerformCreate
)


class TreatmentPlanMapper:
    @staticmethod
    def to_treatment_plan_item_out(
        item: TreatmentPlanItem,
    ) -> TreatmentPlanItemOut:
        return TreatmentPlanItemOut(
            id=item.id,
            procedure_catalog_id=item.procedure_catalog_id,
            procedure_name=item.procedure_catalog.name,
            tooth_numbers=item.tooth_numbers,
            visit_number=item.visit_number,
            priority=item.priority,
            estimated_cost=item.estimated_cost,
            status=item.status,
            performed_procedure_id=item.performed_procedure_id,
            notes=item.notes
        )
        
    @staticmethod
    def to_treatment_plan_out(
        treatment_plan: TreatmentPlan,
    ) -> TreatmentPlanOut:

        return TreatmentPlanOut(
            id=treatment_plan.id,
            encounter_id=treatment_plan.encounter_id,
            patient_id=treatment_plan.patient_id,
            status=treatment_plan.status,
            notes=treatment_plan.notes,
            estimated_total_cost=treatment_plan.estimated_total_cost,
            items=[
                TreatmentPlanMapper.to_treatment_plan_item_out(item)
                for item in treatment_plan.items
            ],
            created_at=treatment_plan.created_at,
            updated_at=treatment_plan.updated_at
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
                TreatmentPlan.tenant_id == tenant_id,
                TreatmentPlan.encounter_id == encounter_id,
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
    
    @staticmethod
    async def get_optional(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
    ) -> TreatmentPlan:

        result = await db.execute(
            select(TreatmentPlan)
            .where(
                TreatmentPlan.tenant_id == tenant_id,
                TreatmentPlan.encounter_id == encounter_id,
            )
            .options(
                selectinload(TreatmentPlan.items)
                .selectinload(
                    TreatmentPlanItem.procedure_catalog
                )
            )
        )

        plan = result.scalar_one_or_none()
        return plan

    @staticmethod
    async def get_item(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
        item_id: UUID,
    ) -> TreatmentPlanItem:

        result = await db.execute(
            select(TreatmentPlanItem)
            .join(TreatmentPlan)
            .where(
                TreatmentPlanItem.id == item_id,
                TreatmentPlan.encounter_id == encounter_id,
                TreatmentPlan.tenant_id == tenant_id,
            )
            .options(
                selectinload(
                    TreatmentPlanItem.procedure_catalog
                ),
                selectinload(
                    TreatmentPlanItem.treatment_plan
                ),
            )
        )

        item = result.scalar_one_or_none()

        if not item:
            raise HTTPException(
                404,
                "Treatment plan item not found",
            )

        return item

class TreatmentPlanService:

    @staticmethod
    async def create_treatment_plan(
        db: AsyncSession,
        tenant_id: UUID,
        patient_id: UUID,
        encounter_id: UUID,
        payload: TreatmentPlanCreate,
    ) -> TreatmentPlanOut:
        existing = await TreatmentPlanRepository.get_optional(
            db,
            tenant_id,
            encounter_id,
        )

        if existing:
            raise HTTPException(
                409,
                "Treatment plan already exists",
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
        
        db.add_all([
            TreatmentPlanItem(
                treatment_plan_id=plan.id,
                **item.model_dump(),
            )
            for item in payload.items
        ])
        
        try:
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(500, "Failed to create treatment plan")

        await db.refresh(plan)
        return TreatmentPlanMapper.to_treatment_plan_out(plan)
    
    
    @staticmethod
    async def get(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
    ) -> TreatmentPlanOut:

        plan = await TreatmentPlanRepository.get_by_encounter(
            db,
            tenant_id,
            encounter_id,
        )

        return TreatmentPlanMapper.to_treatment_plan_out(plan)


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

        item = await TreatmentPlanRepository.get_item(
            db,
            tenant_id,
            encounter_id,
            item_id,
        )

        if item.status == TreatmentPlanItemStatusEnum.DONE:
            raise HTTPException(
                409,
                "Item already completed",
            )

        encounter = await EncounterRepository.get_or_404(
            db,
            tenant_id,
            encounter_id,
        )

        procedure = ProcedureFactory.from_plan_item(
            item=item,
            encounter=encounter,
            performed_by_id=performed_by_id,
            payload=payload,
        )

        db.add(procedure)
        await db.flush()

        item.status = TreatmentPlanItemStatusEnum.DONE
        item.performed_procedure_id = procedure.id

        try:
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(500, "Failed to perform treatment plan item")

        return await TreatmentPlanService.get(
            db,
            tenant_id,
            encounter_id,
        )
        
    @staticmethod
    async def defer_treatment_plan_item(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
        item_id: UUID,
    ) -> TreatmentPlanItemOut:

        item = await TreatmentPlanRepository.get_item(
            db,
            tenant_id,
            encounter_id,
            item_id,
        )

        if item.status == TreatmentPlanItemStatusEnum.DONE:
            raise HTTPException(
                409,
                "Completed items cannot be deferred",
            )

        item.status = TreatmentPlanItemStatusEnum.DEFERRED

        await db.commit()
        await db.refresh(item)
        return TreatmentPlanMapper.to_treatment_plan_item_out(
            item
        )
        
    @staticmethod
    async def cancel_item(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
        item_id: UUID,
    ) -> TreatmentPlanItemOut:

        item = await TreatmentPlanRepository.get_item(
            db,
            tenant_id,
            encounter_id,
            item_id,
        )

        if item.status == TreatmentPlanItemStatusEnum.DONE:
            raise HTTPException(
                409,
                "Completed items cannot be cancelled",
            )

        item.status = TreatmentPlanItemStatusEnum.CANCELLED

        await db.commit()
        await db.refresh(item)
        return TreatmentPlanMapper.to_treatment_plan_item_out(item)
        
        
class TreatmentPlanStatusService:

    @staticmethod
    def refresh(plan: TreatmentPlan):

        pending = any(
            item.status == TreatmentPlanItemStatusEnum.PENDING
            for item in plan.items
        )

        plan.status = (
            TreatmentPlanStatusEnum.ACTIVE
            if pending
            else TreatmentPlanStatusEnum.COMPLETED
        )