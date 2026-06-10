from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models import ClinicalExaminationEntry
from app.taxonomy.registry import TAXONOMY

from app.services.encounter import EncounterRepository
from app.schemas.encounter import (
    ExaminationCreate, 
    ExaminationEntryOut
)

class ExaminationService:

    @staticmethod
    async def upsert_examination(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
        payload: ExaminationCreate,
    ) -> list[ExaminationEntryOut]:

        await EncounterRepository.ensure_encounter_exists(
            db=db,
            tenant_id=tenant_id,
            encounter_id=encounter_id,
        )

        result = await db.execute(
            select(ClinicalExaminationEntry)
            .where(
                ClinicalExaminationEntry.encounter_id
                == encounter_id
            )
        )

        existing_map = {
            entry.field_id: entry
            for entry in result.scalars().all()
        }

        new_entries = []

        for item in payload.entries:
            existing = existing_map.get(
                item.field_id
            )

            if existing:
                existing.category = TAXONOMY.get_field_category(item.field_id),
                existing.value = item.value
            else:
                new_entries.append(
                    ClinicalExaminationEntry(
                        encounter_id=encounter_id,
                        category=TAXONOMY.get_field_category(
                            item.field_id
                        ),
                        field_id=item.field_id,
                        value=item.value,
                    )
                )

        if new_entries:
            db.add_all(new_entries)

        try:
            await db.commit()

        except SQLAlchemyError:
            await db.rollback()

            raise HTTPException(
                status_code=500,
                detail="Failed to save examination",
            )

        result = await db.execute(
            select(ClinicalExaminationEntry)
            .where(
                ClinicalExaminationEntry.encounter_id
                == encounter_id
            )
            .order_by(
                ClinicalExaminationEntry.category,
                ClinicalExaminationEntry.field_id,
            )
        )

        return [
            ExaminationEntryOut.model_validate(entry)
            for entry in result.scalars().all()
        ]
        
    @staticmethod
    async def get_examination_by_encounter_id(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
    ) -> list[ExaminationEntryOut]:

        await EncounterRepository.ensure_encounter_exists(
            db=db,
            tenant_id=tenant_id,
            encounter_id=encounter_id,
        )

        result = await db.execute(
            select(ClinicalExaminationEntry)
            .where(
                ClinicalExaminationEntry.encounter_id == encounter_id
            )
            .order_by(
                ClinicalExaminationEntry.category,
                ClinicalExaminationEntry.field_id,
            )
        )

        return [
            ExaminationEntryOut.model_validate(entry)
            for entry in result.scalars().all()
        ]
        
        
# {
#   "entries": [
#     {
#       "category": "General Examination",
#       "field_id": "gen_built",
#       "value": "Average build, well nourished"
#     },
#     {
#       "category": "General Examination",
#       "field_id": "gen_vitals",
#       "value": "BP 120/80 mmHg, Pulse 78 bpm, Temp 98.6°F"
#     },
#     {
#       "category": "General Examination",
#       "field_id": "gen_pallor",
#       "value": "false"
#     },
#     {
#       "category": "General Examination",
#       "field_id": "gen_edema",
#       "value": "false"
#     },

#     {
#       "category": "Extraoral Examination",
#       "field_id": "ext_symmetry",
#       "value": "Symmetrical"
#     },
#     {
#       "category": "Extraoral Examination",
#       "field_id": "ext_profile",
#       "value": "Straight"
#     },
#     {
#       "category": "Extraoral Examination",
#       "field_id": "ext_tmj",
#       "value": "No clicking or tenderness"
#     },
#     {
#       "category": "Extraoral Examination",
#       "field_id": "ext_lip_competence",
#       "value": "Competent"
#     }
#   ]
# }
# {
#   "entries": [
#     {
#       "category": "Intraoral Soft Tissue Examination",
#       "field_id": "int_hygiene",
#       "value": "Poor"
#     },
#     {
#       "category": "Intraoral Soft Tissue Examination",
#       "field_id": "int_gingival",
#       "value": "Generalized gingival inflammation"
#     },
#     {
#       "category": "Intraoral Soft Tissue Examination",
#       "field_id": "int_bleeding",
#       "value": "true"
#     },
#     {
#       "category": "Intraoral Soft Tissue Examination",
#       "field_id": "int_calculus",
#       "value": "Moderate"
#     },
#     {
#       "category": "Intraoral Soft Tissue Examination",
#       "field_id": "int_salivary",
#       "value": "Normal"
#     },

#     {
#       "category": "Hard Tissue Examination",
#       "field_id": "hard_caries",
#       "value": "true"
#     },
#     {
#       "category": "Hard Tissue Examination",
#       "field_id": "hard_missing",
#       "value": "false"
#     },
#     {
#       "category": "Hard Tissue Examination",
#       "field_id": "hard_sensitivity",
#       "value": "true"
#     }
#   ]
# }
# {
#   "entries": [
#     {
#       "category": "Periodontal Examination",
#       "field_id": "perio_enlargement",
#       "value": "false"
#     },
#     {
#       "category": "Periodontal Examination",
#       "field_id": "perio_recession",
#       "value": "Localized recession on lower incisors"
#     },
#     {
#       "category": "Periodontal Examination",
#       "field_id": "perio_pocket_depth",
#       "value": "4-5 mm pockets in posterior teeth"
#     },
#     {
#       "category": "Periodontal Examination",
#       "field_id": "perio_furcation",
#       "value": "Grade I"
#     },
#     {
#       "category": "Periodontal Examination",
#       "field_id": "perio_plaque_index",
#       "value": "1.8"
#     }
#   ]
# }
# {
#   "entries": [
#     {
#       "category": "Orthodontic Examination",
#       "field_id": "ortho_molar",
#       "value": "Class II Div 1"
#     },
#     {
#       "category": "Orthodontic Examination",
#       "field_id": "ortho_canine",
#       "value": "Class II"
#     },
#     {
#       "category": "Orthodontic Examination",
#       "field_id": "ortho_overjet",
#       "value": "6 mm"
#     },
#     {
#       "category": "Orthodontic Examination",
#       "field_id": "ortho_overbite",
#       "value": "50%"
#     },
#     {
#       "category": "Orthodontic Examination",
#       "field_id": "ortho_crossbite",
#       "value": "false"
#     },
#     {
#       "category": "Orthodontic Examination",
#       "field_id": "ortho_deepbite",
#       "value": "true"
#     }
#   ]
# }
# {
#   "entries": [
#     {
#       "category": "Endodontic Examination",
#       "field_id": "endo_vitality",
#       "value": "Delayed response on tooth #36"
#     },
#     {
#       "category": "Endodontic Examination",
#       "field_id": "endo_thermal",
#       "value": "Lingering pain to cold stimulus"
#     },
#     {
#       "category": "Endodontic Examination",
#       "field_id": "endo_electric",
#       "value": "Positive at high threshold"
#     },
#     {
#       "category": "Endodontic Examination",
#       "field_id": "endo_percussion",
#       "value": "true"
#     },
#     {
#       "category": "Endodontic Examination",
#       "field_id": "endo_swelling",
#       "value": "false"
#     }
#   ]
# }