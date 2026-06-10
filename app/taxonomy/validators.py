"""
Pydantic field validators that plug directly into our existing schemas for encounter.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from pydantic import field_validator, model_validator

from app.taxonomy.registry import TAXONOMY

if TYPE_CHECKING:
    # only for type hints — avoids circular import
    from app.schemas.encounter import (
        MedicalHistoryCreate,
        ExaminationCreate,
        ClinicalFindingsBulkCreate,
        DiagnosisBulkCreate,
        InvestigationsBulkCreate,
    )


# Standalone validator functions
# Call these from @model_validator(mode="after") on your schemas
def validate_medical_history_items(items: list) -> list:
    """
    Validates every item_id in a MedicalHistoryCreate.items list.
    Collects ALL errors before raising — better UX than stopping at first.
    """
    errors = []
    for item in items:
        try:
            TAXONOMY.validate_medical_item_id(item.item_id)
        except ValueError as e:
            errors.append(str(e))
    if errors:
        raise ValueError(errors)
    return items


def validate_examination_entries(entries: list) -> list:
    """
    Validates field_id existence AND value correctness for every
    ExaminationEntryPayload in an ExaminationCreate.entries list.
    """
    errors = []
    for entry in entries:
        try:
            TAXONOMY.validate_exam_entry(entry.field_id, entry.value)
        except ValueError as e:
            errors.append(f"[{entry.field_id}] {e}")
    if errors:
        raise ValueError(errors)
    return entries


def validate_finding_names(findings: list) -> list:
    """
    Validates every finding_name in ClinicalFindingsBulkCreate.findings.
    finding_code and finding_name must BOTH come from DENTAL_PROBLEM_TAXONOMY.
    finding_code == finding_name in our taxonomy (the display string IS the code).
    """
    errors = []
    for finding in findings:
        try:
            TAXONOMY.validate_finding(finding.finding_name)
        except ValueError as e:
            errors.append(str(e))
    if errors:
        raise ValueError(errors)
    return findings

def validate_finding_codes(
    findings: list,
) -> list:
    errors = []

    for finding in findings:
        try:
            TAXONOMY.validate_finding_code(
                finding.finding_code
            )
        except ValueError as e:
            errors.append(str(e))

    if errors:
        raise ValueError(errors)

    return findings

def validate_diagnosis_names(diagnoses: list) -> list:
    """
    Validates every diagnosis_name in DiagnosisBulkCreate.diagnoses.
    Also enforces exactly-one primary at the collection level.
    """
    errors = []
    for dx in diagnoses:
        try:
            TAXONOMY.validate_diagnosis(dx.diagnosis_name)
        except ValueError as e:
            errors.append(str(e))

    primary_count = sum(1 for dx in diagnoses if dx.is_primary)
    if primary_count != 1:
        errors.append(
            f"Exactly one diagnosis must be marked is_primary=True. "
            f"Got {primary_count}."
        )
    if errors:
        raise ValueError(errors)
    return diagnoses


def validate_diagnosis_codes(
    diagnoses: list,
) -> list:
    errors = []

    for diagnosis in diagnoses:
        try:
            TAXONOMY.validate_diagnosis_code(
                diagnosis.diagnosis_code
            )
        except ValueError as e:
            errors.append(str(e))

    primary_count = sum(
        1
        for diagnosis in diagnoses
        if diagnosis.is_primary
    )

    if primary_count != 1:
        errors.append(
            f"Exactly one diagnosis must be marked "
            f"is_primary=True. Got {primary_count}."
        )

    if errors:
        raise ValueError(errors)

    return diagnoses

def validate_investigation_names(investigations: list) -> list:
    """
    Validates every investigation_name in InvestigationsBulkCreate.investigations.
    """
    errors = []
    for inv in investigations:
        try:
            TAXONOMY.validate_investigation(inv.investigation_name)
        except ValueError as e:
            errors.append(str(e))
    if errors:
        raise ValueError(errors)
    return investigations


def validate_investigation_codes(
    investigations: list,
) -> list:
    errors = []

    for inv in investigations:
        try:
            TAXONOMY.validate_investigation_code(
                inv.investigation_code
            )
        except ValueError as e:
            errors.append(str(e))

    if errors:
        raise ValueError(errors)

    return investigations

# Drop-in Pydantic mixin classes
# Inherit from these in your schema classes to auto-attach validators
class MedicalHistoryValidatorMixin:
    @model_validator(mode="after")
    def _validate_items(self):
        validate_medical_history_items(self.items)
        return self


class ExaminationValidatorMixin:
    @model_validator(mode="after")
    def _validate_entries(self):
        validate_examination_entries(self.entries)
        return self


class FindingsValidatorMixin:
    @model_validator(mode="after")
    def _validate_findings(self):
        validate_finding_codes(self.findings)
        return self


class DiagnosisValidatorMixin:
    @model_validator(mode="after")
    def _validate_diagnoses(self):
        validate_diagnosis_codes(self.diagnoses)
        return self


class InvestigationsValidatorMixin:
    @model_validator(mode="after")
    def _validate_investigations(self):
        validate_investigation_codes(self.investigations)
        return self