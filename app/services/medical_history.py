from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models import EncounterMedicalHistory
from app.taxonomy.registry import TAXONOMY

from app.services.encounter import EncounterRepository
from app.schemas.encounter import (
    MedicalHistoryCreate, 
    MedicalHistoryItemPayload,
    MedicalHistoryOut,
)

DENTAL_QUESTION_COLUMN_MAP = {
    "Q_Diabetic": "is_diabetic",
    "Q_Hypertension": "has_hypertension",
    "Q_HeartProblem": "has_heart_condition",
    "Q_MedicineAllergies": "has_medication_allergy",
    "Q_BloodThinners": "is_on_blood_thinners",
    "Q_HepatitisTB": "has_hepatitis_tb",
    "Q_Pregnant": "is_pregnant",
    "Q_SmokeAlcohol": "smokes_or_drinks",
}

class MedicalHistoryService:
    
    @staticmethod
    def _extract_quick_flags(
        items: list[MedicalHistoryItemPayload],
    ) -> dict:

        flags = {
            column: False
            for column in DENTAL_QUESTION_COLUMN_MAP.values()
        }

        for item in items:
            column = DENTAL_QUESTION_COLUMN_MAP.get(item.item_id)

            if column:
                flags[column] = item.is_present

        return flags
        
    @staticmethod
    def _build_medical_history_snapshot(
        payload: MedicalHistoryCreate,
    ) -> list[dict]:
        items = []

        for item in payload.items:
            taxonomy_item = TAXONOMY.get_medical_item(item.item_id)

            items.append({
                "item_id": item.item_id,
                "label": taxonomy_item.label,
                "type": taxonomy_item.type,
                "is_present": item.is_present,
                "notes": item.notes,
            })

        return items

    @staticmethod
    async def upsert_medical_history(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
        payload: MedicalHistoryCreate,
    ) -> MedicalHistoryOut:

        encounter = await EncounterRepository._get_or_404(
            db=db,
            tenant_id=tenant_id,
            encounter_id=encounter_id,
            load_full=True,
        )

        data = payload.model_dump(
            exclude={"items"},
            exclude_unset=True,
        )
        medical_items = MedicalHistoryService._build_medical_history_snapshot(
            payload
        )
        quick_flags = (
            MedicalHistoryService._extract_quick_flags(
                payload.items
            )
        )
            
        if encounter.medical_history:
            history = encounter.medical_history

            history.items = medical_items
            for field, value in quick_flags.items():
                setattr(history, field, value)

        else:
            history = EncounterMedicalHistory(
                encounter_id=encounter_id,
                items=medical_items,
                **quick_flags,
            )

            db.add(history)

        try:
            await db.commit()
            await db.refresh(history)

        except SQLAlchemyError:
            await db.rollback()

            raise HTTPException(
                status_code=500,
                detail="Failed to save medical history",
            )

        return MedicalHistoryOut.model_validate(history)
    
    @staticmethod
    async def get_medical_history_by_encounter_id(
        db: AsyncSession,
        tenant_id: UUID,
        encounter_id: UUID,
    ) -> MedicalHistoryOut:

        encounter = await EncounterRepository._get_or_404(
            db=db,
            tenant_id=tenant_id,
            encounter_id=encounter_id,
            load_full=True,
        )

        if not encounter.medical_history:
            raise HTTPException(
                status_code=404,
                detail="Medical history not found",
            )

        return MedicalHistoryOut.model_validate(
            encounter.medical_history
        )