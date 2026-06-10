import uuid
from datetime import datetime, UTC

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BaseMixin
from app.utils.enums import (
    EncounterStatusEnum,
    TreatmentPlanStatusEnum,
    TreatmentPlanItemStatusEnum,
    InvestigationStatusEnum,
)


# CLINICAL ENCOUNTER
# Central hub for all clinical work done in a single visit.
# One appointment → one encounter
class ClinicalEncounter(Base, BaseMixin):
    __tablename__ = "clinical_encounters"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # enforces 1:1 with appointment
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[EncounterStatusEnum] = mapped_column(
        Enum(EncounterStatusEnum, name="encounter_status_enum"),
        default=EncounterStatusEnum.IN_PROGRESS,
        nullable=False,
    )

    # Chief complaint captured at encounter start
    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Vitals snapshot at time of visit (quick numeric captures)
    bp_systolic: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bp_diastolic: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pulse_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    spo2: Mapped[int | None] = mapped_column(Integer, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    closed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # relationships
    appointment = relationship("Appointment", back_populates="encounter")
    patient = relationship("Patient", back_populates="encounters")
    doctor = relationship("User", foreign_keys=[doctor_id])

    medical_history = relationship(
        "EncounterMedicalHistory",
        back_populates="encounter",
        cascade="all, delete-orphan",
        uselist=False,  # 1:1 per encounter
    )
    examination_findings = relationship(
        "ClinicalExaminationEntry",
        back_populates="encounter",
        cascade="all, delete-orphan",
    )
    clinical_findings = relationship(
        "ClinicalFinding",
        back_populates="encounter",
        cascade="all, delete-orphan",
    )
    diagnoses = relationship(
        "EncounterDiagnosis",
        back_populates="encounter",
        cascade="all, delete-orphan",
    )
    investigations = relationship(
        "Investigation",
        back_populates="encounter",
        cascade="all, delete-orphan",
    )
    treatment_plan = relationship(
        "TreatmentPlan",
        back_populates="encounter",
        cascade="all, delete-orphan",
        uselist=False,  # one plan per encounter; multi-session handled via TreatmentPlanItem.visit_number
    )
    procedures = relationship(
        "Procedure",
        back_populates="encounter",
    )
    # prescriptions = relationship(
    #     "Prescription",
    #     back_populates="encounter",
    #     cascade="all, delete-orphan",       
    # )

    __table_args__ = (
        Index("ix_encounters_tenant_patient", "tenant_id", "patient_id"),
    )


# ENCOUNTER MEDICAL HISTORY  (snapshot per visit)
# NOT stored on the Patient directly.
# Reason: medical history changes over time.
# Each encounter captures what was true at that visit.
#
# items: JSONB list of { item_id, is_present, notes }
# item_id maps to MEDICAL_HISTORY_TAXONOMY keys (static file).
class EncounterMedicalHistory(Base, BaseMixin):
    __tablename__ = "encounter_medical_histories"

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinical_encounters.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # [{ "item_id": "DiabetesMellitus", "is_present": true, "notes": "HbA1c 7.2" }]
    items: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Dental-relevant quick flags (separate columns for fast querying)
    # These mirror DENTAL_RELEVANT_QUESTIONS from the taxonomy
    is_diabetic: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_hypertension: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_heart_condition: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_medication_allergy: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_on_blood_thinners: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_hepatitis_tb: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_pregnant: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    smokes_or_drinks: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    encounter = relationship(
        "ClinicalEncounter",
        back_populates="medical_history",
    )


# CLINICAL EXAMINATION ENTRY  (dynamic key-value per field)
# Each row = one exam field filled in by the doctor.
# category + field_id map to ON_EXAMINATION_TAXONOMY (static).
# value is always a string (boolean checkboxes stored as "true"/"false").
class ClinicalExaminationEntry(Base, BaseMixin):
    __tablename__ = "clinical_examination_entries"

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinical_encounters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Maps to ON_EXAMINATION_TAXONOMY keys
    # e.g. "Intraoral Soft Tissue Examination"
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    # e.g. "int_hygiene"
    field_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # e.g. "Poor", "true", "4-6mm"
    value: Mapped[str] = mapped_column(Text, nullable=False)

    encounter = relationship(
        "ClinicalEncounter",
        back_populates="examination_findings",
    )

    __table_args__ = (
        UniqueConstraint(
            "encounter_id",
            "field_id",
            name="uq_exam_field_per_encounter",
        ),
        Index("ix_exam_encounter", "encounter_id"),
    )


# CLINICAL FINDING  (problems identified this visit)
# finding_code maps to DENTAL_PROBLEM_TAXONOMY (static).
# tooth_numbers is JSONB: [46, 47] using FDI notation.
class ClinicalFinding(Base, BaseMixin):
    __tablename__ = "clinical_findings"

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinical_encounters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # e.g. "Dental Caries (Tooth Decay)"
    finding_code: Mapped[str] = mapped_column(String(200), nullable=False)

    # Human-readable label stored for historical stability
    # finding_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # [46, 47] — FDI tooth numbers
    tooth_numbers: Mapped[list[int] | None] = mapped_column(JSONB, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    encounter = relationship(
        "ClinicalEncounter",
        back_populates="clinical_findings",
    )


# ENCOUNTER DIAGNOSIS
# Converted from findings. Separate from findings because a finding (Pain while chewing) leads to a diagnosis (Irreversible pulpitis). They are not the same thing.
# diagnosis_code maps to DENTAL_DIAGNOSIS_TAXONOMY (static).
class EncounterDiagnosis(Base, BaseMixin):
    __tablename__ = "encounter_diagnoses"

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinical_encounters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # e.g. "Irreversible pulpitis"
    diagnosis_code: Mapped[str] = mapped_column(String(200), nullable=False)
    # diagnosis_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # ICD-10 code for reporting (optional)
    icd10_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Only one primary diagnosis per encounter
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    tooth_numbers: Mapped[list[int] | None] = mapped_column(JSONB, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    encounter = relationship(
        "ClinicalEncounter",
        back_populates="diagnoses",
    )

    __table_args__ = (
        Index("ix_diagnosis_encounter", "encounter_id"),
    )


# INVESTIGATION  (X-rays, blood tests, etc. ordered this visit)
# investigation_code maps to DENTAL_INVESTIGATION_TAXONOMY (static).
# result and result_file_url are filled after completion.
class Investigation(Base, BaseMixin):
    __tablename__ = "investigations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinical_encounters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
    )

    # e.g. "Intraoral periapical radiograph (IOPA)"
    investigation_code: Mapped[str] = mapped_column(String(200), nullable=False)
    # investigation_name: Mapped[str] = mapped_column(String(200), nullable=False)

    status: Mapped[InvestigationStatusEnum] = mapped_column(
        Enum(InvestigationStatusEnum, name="investigation_status_enum"),
        default=InvestigationStatusEnum.REQUESTED,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Filled when investigation is completed
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    encounter = relationship(
        "ClinicalEncounter",
        back_populates="investigations",
    )


# TREATMENT PLAN  (1 per encounter)
# The plan is a container for TreatmentPlanItems.
# Items are grouped by visit_number for multi-session treatments.
# When doctor performs an item now, a Procedure row is created
# and the item.status moves to DONE.
class TreatmentPlan(Base, BaseMixin):
    __tablename__ = "treatment_plans"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinical_encounters.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[TreatmentPlanStatusEnum] = mapped_column(
        Enum(TreatmentPlanStatusEnum, name="treatment_plan_status_enum"),
        default=TreatmentPlanStatusEnum.ACTIVE,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Estimated cost = sum of all item estimated_costs
    # Stored here for quick display without joins
    estimated_total_cost: Mapped[float | None] = mapped_column(Float, nullable=True)

    encounter = relationship(
        "ClinicalEncounter",
        back_populates="treatment_plan",
    )
    items = relationship(
        "TreatmentPlanItem",
        back_populates="treatment_plan",
        cascade="all, delete-orphan",
        order_by="TreatmentPlanItem.visit_number, TreatmentPlanItem.priority",
    )


class TreatmentPlanItem(Base, BaseMixin):
    __tablename__ = "treatment_plan_items"

    treatment_plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("treatment_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    procedure_catalog_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("procedure_catalogs.id", ondelete="RESTRICT"),
        nullable=False,
    )

    tooth_numbers: Mapped[list[int] | None] = mapped_column(JSONB, nullable=True)

    # Which visit this should be done in (1 = this visit, 2 = next, etc.)
    visit_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Priority within the same visit
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[TreatmentPlanItemStatusEnum] = mapped_column(
        Enum(TreatmentPlanItemStatusEnum, name="treatment_plan_item_status_enum"),
        default=TreatmentPlanItemStatusEnum.PENDING,
    )

    # Set when doctor performs this item, links to the resulting Procedure
    performed_procedure_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("procedures.id", ondelete="SET NULL"),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    treatment_plan = relationship(
        "TreatmentPlan",
        back_populates="items",
    )
    procedure_catalog = relationship("ProcedureCatalog")
    performed_procedure = relationship(
        "Procedure",
        foreign_keys=[performed_procedure_id],
    )