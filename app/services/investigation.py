from uuid import UUID
from datetime import datetime, UTC

from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models import Investigation
from app.utils.enums import InvestigationStatusEnum

from app.taxonomy.registry import TAXONOMY

from app.services.encounter import EncounterRepository
from app.schemas.encounter import (
    InvestigationsBulkCreate, 
    InvestigationResultUpdate,
    InvestigationOut
)


class InvestigationMapper:
    @staticmethod
    def to_investigation_out(
        investigation: Investigation,
    ) -> InvestigationOut:

        return InvestigationOut(
            id=investigation.id,
            investigation_code=investigation.investigation_code,
            investigation_name=TAXONOMY.get_investigation_name(
                investigation.investigation_code
            ),
            status=investigation.status,
            notes=investigation.notes,
            result=investigation.result,
            result_file_url=investigation.result_file_url,
            requested_at=investigation.requested_at,
            completed_at=investigation.completed_at if investigation.completed_at else None
        )


class InvestigationRepository:
    @staticmethod
    async def get_or_404(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID, 
        investigation_id: UUID,
    ) -> Investigation:
        result = await db.execute(
            select(Investigation)
            .where(
                and_(
                    Investigation.tenant_id == tenant_id,
                    Investigation.encounter_id == encounter_id,
                    Investigation.id == investigation_id
                )
            )
        )

        investigation = result.scalar_one_or_none()

        if not investigation:
            raise HTTPException(
                404,
                "Investigation data not found",
            )

        return investigation

class InvestigationService:
    
    @staticmethod
    async def get_investigations(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,  
    ) -> list[InvestigationOut]:
        await EncounterRepository.get_or_404(
            db=db,
            tenant_id=tenant_id,
            encounter_id=encounter_id,
        )

        result = await db.execute(
            select(Investigation)
            .where(
                Investigation.encounter_id == encounter_id,
                Investigation.tenant_id == tenant_id
            )
            .order_by(
                Investigation.requested_at,
            )
        )

        investigations =  result.scalars().all()
        return [
            InvestigationMapper.to_investigation_out(inv)
            for inv in investigations
        ]

    @staticmethod
    async def create_investigations(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
        payload: InvestigationsBulkCreate,
    ) -> list[InvestigationOut]:
        
        encounter = await EncounterRepository.get_or_404(
            db=db,
            tenant_id=tenant_id,
            encounter_id=encounter_id,
        )

        investigations = [
            Investigation(
                tenant_id=tenant_id,
                encounter_id=encounter_id,
                patient_id=encounter.patient_id,
                **item.model_dump(),
            )
            for item in payload.investigations
        ]

        db.add_all(investigations)

        try:
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(
                500,
                "Failed to create investigations",
            )
            
        await db.flush()
        return [
            InvestigationMapper.to_investigation_out(inv)
            for inv in investigations
        ]
            
    @staticmethod
    async def update_investigation_result(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
        investigation_id: UUID,
        payload: InvestigationResultUpdate,
    ) -> Investigation:

        investigation = await InvestigationRepository.get_or_404(
            db,
            tenant_id,
            encounter_id,
            investigation_id,
        )

        investigation.result = payload.result
        investigation.result_file_url = payload.result_file_url
        investigation.status = InvestigationStatusEnum(payload.status)

        if investigation.status == InvestigationStatusEnum.COMPLETED:
            investigation.completed_at = datetime.now(UTC)

        try:
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(
                500,
                "Failed to update investigation",
            )
            
        await db.refresh(investigation)
        return InvestigationMapper.to_investigation_out(investigation)