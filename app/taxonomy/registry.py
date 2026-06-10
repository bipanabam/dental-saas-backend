"""
Pre-computed O(1) lookup registry.
Module-level singleton — import TAXONOMY everywhere.

Usage:
    from app.taxonomy.registry import TAXONOMY

    TAXONOMY.validate_medical_item_id("DiabetesMellitus")   # passes silently
    TAXONOMY.validate_finding("Dental Caries (Tooth Decay)") # passes silently
    TAXONOMY.validate_exam_entry("int_hygiene", "Poor")      # passes silently
    TAXONOMY.validate_exam_entry("int_hygiene", "Amazing")   # raises ValueError
"""
from __future__ import annotations

from app.taxonomy.types import ExamField, MedicalHistoryItem
from app.taxonomy.medical_history import (
    MEDICAL_HISTORY_TAXONOMY,
    DENTAL_RELEVANT_QUESTIONS,
)
from app.taxonomy.examination import ON_EXAMINATION_TAXONOMY
from app.taxonomy.clinical import (
    DENTAL_PROBLEM_TAXONOMY,
    DENTAL_DIAGNOSIS_TAXONOMY,
    DENTAL_INVESTIGATION_TAXONOMY,
)


class TaxonomyRegistry:
    """
    Built once at import time. All lookups are O(1) frozenset/dict checks.
    Never instantiate this yourself — use the module-level `TAXONOMY` singleton.
    """

    def __init__(self) -> None:
        # medical history
        self._all_medical_items: dict[str, MedicalHistoryItem] = {
            item.id: item
            for items in MEDICAL_HISTORY_TAXONOMY.values()
            for item in items
        } | {q.id: q for q in DENTAL_RELEVANT_QUESTIONS}

        self._critical_medical_ids: frozenset[str] = frozenset(
            item.id
            for item in self._all_medical_items.values()
            if item.type == "critical"
        )

        # examination
        self._exam_fields: dict[str, ExamField] = {
            f.id: f
            for fields in ON_EXAMINATION_TAXONOMY.values()
            for f in fields
        }
        self._field_to_category: dict[str, str] = {
            field.id: category
            for category, fields in ON_EXAMINATION_TAXONOMY.items()
            for field in fields
        }

        # clinical
        self._finding_names: frozenset[str] = frozenset(
            name
            for names in DENTAL_PROBLEM_TAXONOMY.values()
            for name in names
        )
        self._finding_codes = frozenset(
            code
            for codes in DENTAL_PROBLEM_TAXONOMY.values()
            for code in codes
        )

        self._diagnosis_names: frozenset[str] = frozenset(
            name
            for names in DENTAL_DIAGNOSIS_TAXONOMY.values()
            for name in names
        )
        self._diagnosis_codes = frozenset(
            code
            for codes in DENTAL_DIAGNOSIS_TAXONOMY.values()
            for code in codes
        )

        self._investigation_names: frozenset[str] = frozenset(
            name
            for names in DENTAL_INVESTIGATION_TAXONOMY.values()
            for name in names
        )
        self._investigation_codes = frozenset(
            code
            for codes in DENTAL_INVESTIGATION_TAXONOMY.values()
            for code in codes
        )
        
        self._finding_lookup = {
            name: name
            for names in DENTAL_PROBLEM_TAXONOMY.values()
            for name in names
        }

        self._diagnosis_lookup = {
            name: name
            for names in DENTAL_DIAGNOSIS_TAXONOMY.values()
            for name in names
        }

        self._investigation_lookup = {
            name: name
            for names in DENTAL_INVESTIGATION_TAXONOMY.values()
            for name in names
        }

    # validation helpers (raise ValueError on failure)
    def validate_medical_item_id(self, item_id: str) -> None:
        if item_id not in self._all_medical_items:
            raise ValueError(
                f"Unknown medical history item_id: '{item_id}'. "
                f"Must be one of the ids defined in MEDICAL_HISTORY_TAXONOMY "
                f"or DENTAL_RELEVANT_QUESTIONS."
            )

    def validate_exam_entry(self, field_id: str, value: str) -> None:
        field = self._exam_fields.get(field_id)
        if field is None:
            raise ValueError(
                f"Unknown exam field_id: '{field_id}'. "
                f"Must be one of the ids defined in ON_EXAMINATION_TAXONOMY."
            )
        if field.type == "checkbox":
            if value not in ("true", "false"):
                raise ValueError(
                    f"Field '{field_id}' is a checkbox. "
                    f"Value must be 'true' or 'false', got '{value}'."
                )
        elif field.type == "select":
            if value not in field.options:
                raise ValueError(
                    f"Field '{field_id}' is a select. "
                    f"Allowed values: {list(field.options)}. Got: '{value}'."
                )
        elif field.type == "text":
            if not value.strip():
                raise ValueError(
                    f"Field '{field_id}' is a text field and cannot be empty."
                )

    def validate_finding(self, finding_name: str) -> None:
        if finding_name not in self._finding_names:
            raise ValueError(
                f"Unknown finding: '{finding_name}'. "
                f"Must be a value from DENTAL_PROBLEM_TAXONOMY."
            )
            
    def validate_finding_code(
        self,
        finding_code: str,
    ) -> None:
        if finding_code not in self._finding_codes:
            raise ValueError(
                f"Unknown finding code: '{finding_code}'."
            )

    def validate_diagnosis(self, diagnosis_name: str) -> None:
        if diagnosis_name not in self._diagnosis_names:
            raise ValueError(
                f"Unknown diagnosis: '{diagnosis_name}'. "
                f"Must be a value from DENTAL_DIAGNOSIS_TAXONOMY."
            )
            
    def validate_diagnosis_code(
        self,
        diagnosis_code: str,
    ) -> None:
        if diagnosis_code not in self._diagnosis_codes:
            raise ValueError(
                f"Unknown diagnosis code: '{diagnosis_code}'."
            )

    def validate_investigation(self, investigation_name: str) -> None:
        if investigation_name not in self._investigation_names:
            raise ValueError(
                f"Unknown investigation: '{investigation_name}'. "
                f"Must be a value from DENTAL_INVESTIGATION_TAXONOMY."
            )
            
    def validate_investigation_code(
        self,
        investigation_code: str,
    ) -> None:
        if investigation_code not in self._investigation_codes:
            raise ValueError(
                f"Unknown investigation code: '{investigation_code}'."
            )

    # boolean checks (no raise — use in conditions)
    def is_critical_medical_item(self, item_id: str) -> bool:
        return item_id in self._critical_medical_ids

    def get_exam_field(self, field_id: str) -> ExamField | None:
        return self._exam_fields.get(field_id)
    
    def get_field_category(self, field_id: str) -> str | None:
        return self._field_to_category.get(field_id)

    def get_medical_item(self, item_id: str) -> MedicalHistoryItem | None:
        return self._all_medical_items.get(item_id)
    
    def get_finding_name(self, code: str) -> str | None:
        return self._finding_lookup.get(code)

    def get_diagnosis_name(self, code: str) -> str | None:
        return self._diagnosis_lookup.get(code)

    def get_investigation_name(self, code: str) -> str | None:
        return self._investigation_lookup.get(code)

    # API endpoint helpers
    def to_api_dict(self) -> dict:
        """
        Returns the full taxonomy as a JSON-serialisable dict.
        Served by GET /api/v1/taxonomy: frontend fetches this once
        and uses it to build forms dynamically.
        """
        return {
            "medical_history": {
                category: [
                    {"id": item.id, "label": item.label, "type": item.type}
                    for item in items
                ]
                for category, items in MEDICAL_HISTORY_TAXONOMY.items()
            },
            "dental_relevant_questions": [
                {"id": q.id, "label": q.label, "type": q.type}
                for q in DENTAL_RELEVANT_QUESTIONS
            ],
            "examination": {
                category: [
                    {
                        "id": f.id,
                        "label": f.label,
                        "type": f.type,
                        **({"options": list(f.options)} if f.options else {}),
                    }
                    for f in fields
                ]
                for category, fields in ON_EXAMINATION_TAXONOMY.items()
            },
            "findings": {
                cat: names for cat, names in DENTAL_PROBLEM_TAXONOMY.items()
            },
            "diagnoses": {
                cat: names for cat, names in DENTAL_DIAGNOSIS_TAXONOMY.items()
            },
            "investigations": {
                cat: names for cat, names in DENTAL_INVESTIGATION_TAXONOMY.items()
            },
        }

TAXONOMY = TaxonomyRegistry()