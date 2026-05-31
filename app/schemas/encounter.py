from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


# ENCOUNTER
class EncounterCreate(BaseModel):
    """
    Auto-created inside start_appointment() service.
    Exposed here so the endpoint can accept an optional
    chief complaint override at start time.
    """
    chief_complaint: str | None = None
    bp_systolic: int | None = None
    bp_diastolic: int | None = None
    pulse_rate: int | None = None
    temperature: float | None = None
    weight_kg: float | None = None
    spo2: int | None = None


class EncounterUpdate(BaseModel):
    chief_complaint: str | None = None
    bp_systolic: int | None = None
    bp_diastolic: int | None = None
    pulse_rate: int | None = None
    temperature: float | None = None
    weight_kg: float | None = None
    spo2: int | None = None


class EncounterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    appointment_id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID | None
    status: str
    chief_complaint: str | None
    bp_systolic: int | None
    bp_diastolic: int | None
    pulse_rate: int | None
    temperature: float | None
    weight_kg: float | None
    spo2: int | None
    started_at: datetime
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EncounterDetail(EncounterOut):
    """Full encounter with all nested clinical data."""
    medical_history: MedicalHistoryOut | None = None
    examination_findings: list[ExaminationEntryOut] = []
    clinical_findings: list[ClinicalFindingOut] = []
    diagnoses: list[DiagnosisOut] = []
    investigations: list[InvestigationOut] = []
    treatment_plan: TreatmentPlanOut | None = None
    procedures: list[ProcedureSummary] = []


# MEDICAL HISTORY
class MedicalHistoryItemPayload(BaseModel):
    item_id: str       # maps to MEDICAL_HISTORY_TAXONOMY
    is_present: bool
    notes: str | None = None


class MedicalHistoryCreate(BaseModel):
    """
    POST /encounters/{id}/history
    """
    items: list[MedicalHistoryItemPayload]

    # Dental quick-flags — extracted and stored as dedicated columns
    # so receptionists can query "all diabetic patients" fast.
    is_diabetic: bool | None = None
    has_hypertension: bool | None = None
    has_heart_condition: bool | None = None
    has_medication_allergy: bool | None = None
    is_on_blood_thinners: bool | None = None
    has_hepatitis_tb: bool | None = None
    is_pregnant: bool | None = None
    smokes_or_drinks: bool | None = None


class MedicalHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    encounter_id: uuid.UUID
    items: list[dict[str, Any]] | None
    is_diabetic: bool | None
    has_hypertension: bool | None
    has_heart_condition: bool | None
    has_medication_allergy: bool | None
    is_on_blood_thinners: bool | None
    has_hepatitis_tb: bool | None
    is_pregnant: bool | None
    smokes_or_drinks: bool | None
    updated_at: datetime


# CLINICAL EXAMINATION
class ExaminationEntryPayload(BaseModel):
    category: str    # e.g. "Intraoral Soft Tissue Examination"
    field_id: str    # e.g. "int_hygiene"
    value: str       # e.g. "Poor", "true", "4-6mm"


class ExaminationCreate(BaseModel):
    """
    POST /encounters/{id}/examination
    Send as a batch — all entries upserted together.
    Frontend sends the full filled-in form.
    """
    entries: list[ExaminationEntryPayload]


class ExaminationEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    field_id: str
    value: str


# CLINICAL FINDINGS
class ClinicalFindingCreate(BaseModel):
    finding_code: str        # from DENTAL_PROBLEM_TAXONOMY
    finding_name: str        # stored for historical stability
    tooth_numbers: list[int] | None = None
    notes: str | None = None


class ClinicalFindingsBulkCreate(BaseModel):
    """POST /encounters/{id}/findings — send all at once."""
    findings: list[ClinicalFindingCreate]


class ClinicalFindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    finding_code: str
    finding_name: str
    tooth_numbers: list[int] | None
    notes: str | None


# DIAGNOSIS
class DiagnosisCreate(BaseModel):
    diagnosis_code: str      # from DENTAL_DIAGNOSIS_TAXONOMY
    diagnosis_name: str
    icd10_code: str | None = None
    is_primary: bool = False
    tooth_numbers: list[int] | None = None
    notes: str | None = None


class DiagnosisBulkCreate(BaseModel):
    """
    POST /encounters/{id}/diagnoses
    Exactly one item must have is_primary=True.
    Validated at the schema level.
    """
    diagnoses: list[DiagnosisCreate]

    @model_validator(mode="after")
    def validate_primary(self) -> "DiagnosisBulkCreate":
        primary_count = sum(1 for d in self.diagnoses if d.is_primary)
        if primary_count != 1:
            raise ValueError(
                "Exactly one diagnosis must be marked as primary."
            )
        return self


class DiagnosisUpdate(BaseModel):
    diagnosis_code: str | None = None
    diagnosis_name: str | None = None
    icd10_code: str | None = None
    is_primary: bool | None = None
    tooth_numbers: list[int] | None = None
    notes: str | None = None


class DiagnosisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    diagnosis_code: str
    diagnosis_name: str
    icd10_code: str | None
    is_primary: bool
    tooth_numbers: list[int] | None
    notes: str | None


# INVESTIGATION
class InvestigationCreate(BaseModel):
    investigation_code: str  # from DENTAL_INVESTIGATION_TAXONOMY
    investigation_name: str
    notes: str | None = None


class InvestigationsBulkCreate(BaseModel):
    """POST /encounters/{id}/investigations"""
    investigations: list[InvestigationCreate]


class InvestigationResultUpdate(BaseModel):
    """PATCH /encounters/{encounter_id}/investigations/{id}/result"""
    result: str | None = None
    result_file_url: str | None = None
    status: str  # COMPLETED or CANCELLED


class InvestigationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    investigation_code: str
    investigation_name: str
    status: str
    notes: str | None
    result: str | None
    result_file_url: str | None
    requested_at: datetime
    completed_at: datetime | None


# TREATMENT PLAN
class TreatmentPlanItemCreate(BaseModel):
    procedure_catalog_id: uuid.UUID
    tooth_numbers: list[int] | None = None
    visit_number: int = 1          # 1 = this visit, 2 = next, etc.
    priority: int = 1
    estimated_cost: float | None = None
    notes: str | None = None


class TreatmentPlanCreate(BaseModel):
    """
    POST /encounters/{id}/treatment-plan
    Creates the plan and all its items in one shot.
    """
    notes: str | None = None
    items: list[TreatmentPlanItemCreate]


class TreatmentPlanItemPerformCreate(BaseModel):
    """
    POST /encounters/{encounter_id}/treatment-plan/items/{item_id}/perform
    Doctor decides to perform this item NOW.
    Creates a Procedure and marks the item DONE.
    """
    final_cost: float | None = None
    notes: str | None = None
    performed_duration_minutes: int | None = None


class TreatmentPlanItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    procedure_catalog_id: uuid.UUID
    procedure_name: str | None = None  # resolved from catalog
    tooth_numbers: list[int] | None
    visit_number: int
    priority: int
    estimated_cost: float | None
    status: str
    performed_procedure_id: uuid.UUID | None
    notes: str | None


class TreatmentPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    encounter_id: uuid.UUID
    patient_id: uuid.UUID
    status: str
    notes: str | None
    estimated_total_cost: float | None
    items: list[TreatmentPlanItemOut] = []
    created_at: datetime
    updated_at: datetime


# SHARED SUMMARY (used in EncounterDetail)
class ProcedureSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str | None
    tooth_numbers: list[int] | None
    status: str
    final_cost: float | None
    procedure_date: datetime | None


# forward refs
EncounterDetail.model_rebuild()