import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    Boolean,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    DateTime
)

from app.core.database import Base
from app.models.base import BaseMixin
from app.utils.enums import ProcedureStatusEnum, ProcedureCategoryEnum


class ProcedureCatalog(Base, BaseMixin):
    __tablename__ = "procedure_catalogs"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    category: Mapped[ProcedureCategoryEnum] = mapped_column(
        Enum(ProcedureCategoryEnum, name="procedure_category_enum"),
        default=ProcedureCategoryEnum.OTHER,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    default_duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    default_cost: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    procedures = relationship(
        "Procedure",
        back_populates="procedure_catalog",
    )
    appointment_procedures = relationship(
        "AppointmentProcedure",
        back_populates="procedure_catalog",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "code",
            name="uq_procedure_code_per_tenant",
        ),
    )


class Procedure(Base, BaseMixin):
    """Actual performed clinical work"""
    __tablename__ = "procedures"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinical_encounters.id", ondelete="CASCADE"),
        nullable=False,
    )

    procedure_catalog_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("procedure_catalogs.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    tooth_numbers: Mapped[list[int] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    status: Mapped[ProcedureStatusEnum] = mapped_column(
        Enum(ProcedureStatusEnum, name="procedure_status_enum"),
        default=ProcedureStatusEnum.PENDING,
    )

    estimated_cost: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    final_cost: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    procedure_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    performed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    performed_duration_minutes:  Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # When planned procedure eventually became an actual Procedure or more Procedures
    appointment_procedure_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("appointment_procedures.id", ondelete="SET NULL"),
        nullable=True,
    )

    # relationship
    appointment = relationship(
        "Appointment",
        back_populates="procedures",
    )
    appointment_procedure = relationship(
        "AppointmentProcedure",
        back_populates="procedures",
    )
    encounter = relationship(
        "ClinicalEncounter",
        back_populates="procedures",
    )
    procedure_catalog = relationship(
        "ProcedureCatalog",
        back_populates="procedures",
    )