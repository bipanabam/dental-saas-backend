from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models import EncounterDiagnosis
from app.taxonomy.registry import TAXONOMY

from app.services.encounter import EncounterRepository
from app.schemas.encounter import (
    DiagnosisBulkCreate, 
    DiagnosisOut
)


class DiagnosisMapper:
    @staticmethod
    def to_diagnosis_out(
        diagnosis: EncounterDiagnosis,
    ) -> DiagnosisOut:

        return DiagnosisOut(
            id=diagnosis.id,
            diagnosis_code=diagnosis.diagnosis_code,
            diagnosis_name=TAXONOMY.get_diagnosis_name(
                diagnosis.diagnosis_code
            ),
            icd10_code=diagnosis.icd10_code,
            is_primary=diagnosis.is_primary,
            tooth_numbers=diagnosis.tooth_numbers,
            notes=diagnosis.notes,
        )


class DiagnosisService:
    
    @staticmethod
    async def get_diagnoses(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
    ) -> list[DiagnosisOut]:

        await EncounterRepository.get_or_404(
            db=db,
            tenant_id=tenant_id,
            encounter_id=encounter_id,
        )

        result = await db.execute(
            select(EncounterDiagnosis)
            .where(
                EncounterDiagnosis.encounter_id == encounter_id,
            )
            .order_by(
                EncounterDiagnosis.is_primary.desc(),
                EncounterDiagnosis.created_at,
            )
        )

        diagnoses =  result.scalars().all()
        return [
            DiagnosisMapper.to_diagnosis_out(daignosis)
            for daignosis in diagnoses
        ]

    @staticmethod
    async def replace_diagnoses(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
        payload: DiagnosisBulkCreate,
    ) -> list[DiagnosisOut]:

        encounter = await EncounterRepository.get_or_404(
            db=db,
            tenant_id=tenant_id,
            encounter_id=encounter_id,
            load_full=True,
        )

        encounter.diagnoses.clear()

        encounter.diagnoses.extend(
            EncounterDiagnosis(
                diagnosis_code=d.diagnosis_code,
                icd10_code=d.icd10_code,
                is_primary=d.is_primary,
                tooth_numbers=d.tooth_numbers,
                notes=d.notes,
            )
            for d in payload.diagnoses
        )

        try:
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Failed to save diagnoses",
            )

        await db.refresh(encounter)

        return [
            DiagnosisMapper.to_diagnosis_out(diagnosis)
            for diagnosis in encounter.diagnoses
        ]
    
# convert_finding_to_diagnosis()
# {
#   "diagnoses": [
#     {
#       "diagnosis_code": "Irreversible pulpitis",
#       "diagnosis_name": "Irreversible pulpitis",
#       "is_primary": true,
#       "tooth_numbers": [46],
#       "notes": "Based on symptoms and vitality testing"
#     }
#   ]
# }
# {
#   "diagnoses": [
#     {
#       "diagnosis_code": "Irreversible pulpitis",
#       "diagnosis_name": "Irreversible pulpitis",
#       "icd10_code": "K04.0",
#       "is_primary": true,
#       "tooth_numbers": [46],
#       "notes": "Confirmed by vitality testing"
#     },
#     {
#       "diagnosis_code": "Generalized chronic gingivitis",
#       "diagnosis_name": "Generalized chronic gingivitis",
#       "icd10_code": null,
#       "is_primary": false,
#       "tooth_numbers": null,
#       "notes": null
#     }
#   ]
# }
# {
#   "diagnoses": [
#     {
#       "diagnosis_code": "Class II malocclusion",
#       "diagnosis_name": "Class II malocclusion",
#       "icd10_code": null,
#       "is_primary": true,
#       "tooth_numbers": null,
#       "notes": "Skeletal Class II pattern"
#     },
#     {
#       "diagnosis_code": "Crowding",
#       "diagnosis_name": "Crowding",
#       "icd10_code": null,
#       "is_primary": false,
#       "tooth_numbers": [11, 12, 13, 21, 22, 23],
#       "notes": "Anterior crowding"
#     }
#   ]
# }
# {
#   "investigations": [
#     {
#       "investigation_code": "Orthopantomogram (OPG)",
#       "investigation_name": "Orthopantomogram (OPG)",
#       "notes": "Evaluate impacted third molar"
#     },
#     {
#       "investigation_code": "Complete blood count (CBC)",
#       "investigation_name": "Complete blood count (CBC)",
#       "notes": "Pre-surgical screening"
#     }
#   ]
# }