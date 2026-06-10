from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models import ClinicalFinding, ClinicalEncounter
from app.taxonomy.registry import TAXONOMY

from app.services.encounter import EncounterRepository
from app.schemas.encounter import (
    ClinicalFindingsBulkCreate,
    ClinicalFindingOut
)

class FindingMapper:
    @staticmethod
    def to_finding_out(
        finding: ClinicalFinding,
    ) -> ClinicalFindingOut:

        return ClinicalFindingOut(
            id=finding.id,
            finding_code=finding.finding_code,
            finding_name=TAXONOMY.get_finding_name(
                finding.finding_code
            ),
            tooth_numbers=finding.tooth_numbers,
            notes=finding.notes,
        )

class FindingService:
    
    @staticmethod
    async def get_findings_by_encounter_id(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
    ) -> list[ClinicalFindingOut]:

        await EncounterRepository.get_or_404(
            db=db,
            tenant_id=tenant_id,
            encounter_id=encounter_id,
        )

        result = await db.execute(
            select(ClinicalFinding)
            .where(
                ClinicalFinding.encounter_id == encounter_id
            )
            .order_by(ClinicalFinding.created_at)
        )
        clinical_findings = result.scalars().all()

        return [
            FindingMapper.to_finding_out(finding)
            for finding in clinical_findings
        ]

    @staticmethod
    async def create_findings(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
        payload: ClinicalFindingsBulkCreate,
    ) -> list[ClinicalFindingOut]:

        await EncounterRepository.get_or_404(
            db=db,
            tenant_id=tenant_id,
            encounter_id=encounter_id,
        )

        findings = [
            ClinicalFinding(
                encounter_id=encounter_id,
                finding_code=f.finding_code,
                tooth_numbers=f.tooth_numbers,
                notes=f.notes,
            )
            for f in payload.findings
        ]

        db.add_all(findings)

        try:
            await db.commit()

        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Failed to save findings",
            )
        
        await db.flush()

        return [
            FindingMapper.to_finding_out(f)
            for f in findings
        ]
    
    @staticmethod
    async def replace_findings(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
        payload: ClinicalFindingsBulkCreate,
    ) -> list[ClinicalFinding]:

        encounter = await EncounterRepository.get_or_404(
            db=db,
            tenant_id=tenant_id,
            encounter_id=encounter_id,
            load_full=True,
        )

        encounter.clinical_findings.clear()

        encounter.clinical_findings.extend(
            ClinicalFinding(
                finding_code=f.finding_code,
                tooth_numbers=f.tooth_numbers,
                notes=f.notes,
            )
            for f in payload.findings
        )

        try:
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Failed to save findings",
            )

        await db.refresh(encounter)

        return [
            FindingMapper.to_finding_out(finding)
            for finding in encounter.clinical_findings
        ]

    @staticmethod
    async def delete_finding(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
        finding_id: UUID,
    ) -> None:

        stmt = (
            select(ClinicalFinding)
            .join(ClinicalEncounter)
            .where(
                ClinicalFinding.id == finding_id,
                ClinicalFinding.encounter_id == encounter_id,
                ClinicalEncounter.tenant_id == tenant_id,
            )
        )

        finding = await db.scalar(stmt)

        if not finding:
            raise HTTPException(
                status_code=404,
                detail="Finding not found",
            )
            
        try:
            await db.delete(finding)
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Failed to delete finding.",
            )
        
# # Example: Patient has caries on tooth 46 and gingivitis.       
# {
#   "findings": [
#     {
#       "finding_code": "Dental Caries (Tooth Decay)",
#       "finding_name": "Dental Caries (Tooth Decay)",
#       "tooth_numbers": [46],
#       "notes": "Deep occlusal caries"
#     },
#     {
#       "finding_code": "Gingivitis",
#       "finding_name": "Gingivitis",
#       "tooth_numbers": null,
#       "notes": "Generalized marginal inflammation"
#     }
#   ]
# }
# # Multiple teeth
# {
#   "findings": [
#     {
#       "finding_code": "Sensitive Teeth",
#       "finding_name": "Sensitive Teeth",
#       "tooth_numbers": [14, 15, 16],
#       "notes": "Cold sensitivity"
#     },
#     {
#       "finding_code": "Food Lodgement",
#       "finding_name": "Food Lodgement",
#       "tooth_numbers": [26, 27],
#       "notes": "Open contact area"
#     }
#   ]
# }
# {
#   "findings": [
#     {
#       "finding_code": "Severe Tooth Pain",
#       "finding_name": "Severe Tooth Pain",
#       "tooth_numbers": [36],
#       "notes": "Pain worsens at night"
#     },
#     {
#       "finding_code": "Facial Swelling",
#       "finding_name": "Facial Swelling",
#       "tooth_numbers": [36],
#       "notes": "Left mandibular swelling"
#     }
#   ]
# }