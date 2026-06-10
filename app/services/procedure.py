from datetime import datetime, UTC
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.models import ClinicalEncounter, TreatmentPlanItem, Procedure, ProcedureCatalog

from app.services.encounter import EncounterRepository

from app.schemas.encounter import TreatmentPlanItemPerformCreate, ProcedureSummary
from app.schemas.procedure import ProcedureUpdate, ProcedureOut, ProcedureCreate

from app.utils.enums import ProcedureStatusEnum, TreatmentPlanItemStatusEnum, EncounterStatusEnum

    
class ProcedureRepository:

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        tenant_id: UUID,
        procedure_id: UUID,
    ) -> Procedure:

        result = await db.execute(
            select(Procedure)
            .where(
                Procedure.id == procedure_id,
                Procedure.tenant_id == tenant_id,
            )
            .options(
                selectinload(Procedure.procedure_catalog),
                selectinload(Procedure.encounter),
            )
        )

        procedure = result.scalar_one_or_none()

        if not procedure:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Procedure not found",
            )

        return procedure

    @staticmethod
    async def get_by_encounter(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
    ) -> list[Procedure]:

        result = await db.execute(
            select(Procedure)
            .where(
                Procedure.tenant_id == tenant_id,
                Procedure.encounter_id == encounter_id,
            )
            .options(
                selectinload(Procedure.procedure_catalog),
            )
            .order_by(
                Procedure.procedure_date.desc()
            )
        )

        return list(result.scalars().all())   
    
    
class ProcedureCatalogRepository:

    @staticmethod
    async def get_or_404(
        db: AsyncSession,
        procedure_catalog_id: UUID,
    ) -> ProcedureCatalog:

        result = await db.execute(
            select(ProcedureCatalog)
            .where(
                ProcedureCatalog.id
                == procedure_catalog_id
            )
        )

        catalog = result.scalar_one_or_none()

        if not catalog:
            raise HTTPException(
                404,
                "Procedure catalog not found",
            )

        return catalog 

class ProcedureFactory:

    @staticmethod
    def from_plan_item(
        item: TreatmentPlanItem,
        encounter: ClinicalEncounter,
        performed_by_id: UUID,
        payload: TreatmentPlanItemPerformCreate,
    ) -> Procedure:

        now = datetime.now(UTC)

        return Procedure(
            tenant_id=encounter.tenant_id,
            patient_id=encounter.patient_id,
            appointment_id=encounter.appointment_id,
            encounter_id=encounter.id,

            procedure_catalog_id=item.procedure_catalog_id,

            tooth_numbers=item.tooth_numbers,

            status=ProcedureStatusEnum.COMPLETED,

            estimated_cost=item.estimated_cost,

            final_cost=(
                payload.final_cost
                or item.estimated_cost
            ),

            description=payload.notes,

            performed_by_id=performed_by_id,

            performed_duration_minutes=(
                payload.performed_duration_minutes
            ),

            procedure_date=now,
            completed_at=now,
        )
        
class ProcedureMapper:

    @staticmethod
    def to_summary(
        procedure: Procedure,
    ) -> ProcedureSummary:

        return ProcedureSummary(
            id=procedure.id,
            name=(
                procedure.procedure_catalog.name
                if procedure.procedure_catalog
                else None
            ),
            tooth_numbers=procedure.tooth_numbers,
            status=procedure.status,
            final_cost=procedure.final_cost,
            procedure_date=procedure.procedure_date,
        )

    @staticmethod
    def to_detail(
        procedure: Procedure,
    ) -> ProcedureOut:

        return ProcedureOut(
            id=procedure.id,
            encounter_id=procedure.encounter_id,
            patient_id=procedure.patient_id,

            procedure_catalog_id=procedure.procedure_catalog_id,

            procedure_name=(
                procedure.procedure_catalog.name
                if procedure.procedure_catalog
                else None
            ),

            tooth_numbers=procedure.tooth_numbers,

            status=procedure.status,

            estimated_cost=procedure.estimated_cost,
            final_cost=procedure.final_cost,

            description=procedure.description,

            performed_by_id=procedure.performed_by_id,

            performed_duration_minutes=(
                procedure.performed_duration_minutes
            ),

            procedure_date=procedure.procedure_date,
            completed_at=procedure.completed_at,
        )
        
        
        
class ProcedureService:

    @staticmethod
    async def list_by_encounter(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
    ) -> list[ProcedureSummary]:

        procedures = (
            await ProcedureRepository.get_by_encounter(
                db,
                tenant_id,
                encounter_id,
            )
        )

        return [
            ProcedureMapper.to_summary(p)
            for p in procedures
        ]
        
    @staticmethod
    async def get(
        db: AsyncSession,
        tenant_id: UUID,
        procedure_id: UUID,
    ) -> ProcedureOut:

        procedure = (
            await ProcedureRepository.get_by_id(
                db,
                tenant_id,
                procedure_id,
            )
        )

        return ProcedureMapper.to_detail(
            procedure
        )
        
    @staticmethod
    async def update(
        db: AsyncSession,
        tenant_id: UUID,
        procedure_id: UUID,
        payload: ProcedureUpdate,
    ) -> ProcedureOut:

        procedure = (
            await ProcedureRepository.get_by_id(
                db,
                tenant_id,
                procedure_id,
            )
        )

        if payload.description is not None:
            procedure.description = payload.description

        if payload.final_cost is not None:
            procedure.final_cost = payload.final_cost

        if payload.performed_duration_minutes is not None:
            procedure.performed_duration_minutes = (
                payload.performed_duration_minutes
            )

        await db.commit()
        await db.refresh(procedure)

        return ProcedureMapper.to_detail(
            procedure
        )
        
    @staticmethod
    async def create(
        db: AsyncSession,
        tenant_id: UUID,
        performed_by_id: UUID,
        encounter_id: UUID,
        payload: ProcedureCreate,
    ) -> ProcedureOut:
        encounter = await EncounterRepository.get_or_404(
            db=db,
            tenant_id=tenant_id,
            encounter_id=encounter_id,
        )
        
        if (encounter.status != EncounterStatusEnum.IN_PROGRESS):
            raise HTTPException(
                400,
                "Cannot create procedure for closed encounter",
            )
            
        catalog = (
            await ProcedureCatalogRepository.get_or_404(
                db,
                payload.procedure_catalog_id,
            )
        )
        
        now = datetime.now(UTC)

        procedure = Procedure(
            tenant_id=tenant_id,
            patient_id=encounter.patient_id,
            appointment_id=encounter.appointment_id,
            encounter_id=encounter.id,
            procedure_catalog_id=payload.procedure_catalog_id,
            description=payload.description,
            tooth_numbers=payload.tooth_numbers,
            status=ProcedureStatusEnum.COMPLETED,
            estimated_cost=(
                payload.estimated_cost
                or catalog.default_cost
            ),
            final_cost=(
                payload.final_cost
                or payload.estimated_cost
                or catalog.default_cost
            ),
            performed_by_id=performed_by_id,
            performed_duration_minutes=(
                payload.performed_duration_minutes
            ),
            procedure_date=now,
            completed_at=now,
        )
        
        db.add(procedure)

        try:
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()

            raise HTTPException(
                500,
                "Failed to create procedure",
            )
        return ProcedureMapper.to_detail(procedure)
        
class ProcedureCancellationService:

    @staticmethod
    async def cancel(
        db: AsyncSession,
        tenant_id: UUID,
        procedure_id: UUID,
    ) -> ProcedureOut:

        procedure = (
            await ProcedureRepository.get_by_id(
                db,
                tenant_id,
                procedure_id,
            )
        )
        
        if procedure.status == ProcedureStatusEnum.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot cancel completed procedure.",
            )

        if procedure.status == ProcedureStatusEnum.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Procedure already cancelled",
            )

        procedure.status = (
            ProcedureStatusEnum.CANCELLED
        )

        result = await db.execute(
            select(TreatmentPlanItem)
            .where(
                TreatmentPlanItem.performed_procedure_id
                == procedure.id
            )
        )

        item = result.scalar_one_or_none()

        if item:
            item.status = (
                TreatmentPlanItemStatusEnum.PENDING
            )

            item.performed_procedure_id = None

        await db.commit()
        await db.refresh(procedure)

        return ProcedureMapper.to_detail(
            procedure
        )