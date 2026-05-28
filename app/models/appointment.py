from datetime import datetime
import uuid

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
    Float,
    UniqueConstraint
)

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base
from app.models.base import BaseMixin
from app.utils.enums import (
    AppointmentTypeEnum,
    AppointmentStatusEnum,
    AppointmentSourceEnum,
    AppointmentCancellationReasonEnum,
    AppointmentProcedureStatusEnum,
    PaymentStatusEnum,
)


class Appointment(Base, BaseMixin):
    __tablename__ = "appointments"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    appointment_type: Mapped[AppointmentTypeEnum] = mapped_column(
        Enum(AppointmentTypeEnum, name="appointment_type_enum"),
        default=AppointmentTypeEnum.BOOKED,
    )
    appointment_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        default=30,
    )
    chief_complaint: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    source: Mapped[AppointmentSourceEnum] = mapped_column(
        Enum(AppointmentSourceEnum, name="appointment_source_enum"),
        default=AppointmentSourceEnum.FRONT_DESK,
    ) # for analytics
    status: Mapped[AppointmentStatusEnum] = mapped_column(
        Enum(AppointmentStatusEnum, name="appointment_status_enum"),
        default=AppointmentStatusEnum.BOOKED,
    )
    payment_status: Mapped[PaymentStatusEnum] = mapped_column(
        Enum(PaymentStatusEnum, name="payment_status_enum"),
        default=PaymentStatusEnum.PENDING,
    )
    
    cancellation_reason_type: Mapped[
        AppointmentCancellationReasonEnum | None
    ] = mapped_column(
        Enum(
            AppointmentCancellationReasonEnum,
            name="appointment_cancellation_reason_enum",
        ),
        nullable=True,
    )
    cancellation_reason_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    follow_up_from_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("appointments.id", ondelete="SET NULL"),
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

    # relationships
    planned_procedures = relationship(
        "AppointmentProcedure",
        back_populates="appointment",
        cascade="all, delete-orphan",
    )
    procedures = relationship(
        "Procedure",
        back_populates="appointment",
        cascade="all, delete-orphan",
    )
    queue_entry = relationship(
        "Queue",
        back_populates="appointment",
        uselist=False,
        cascade="all, delete-orphan",
    )
    patient = relationship(
        "Patient",
        back_populates="appointments",
    )

    doctor = relationship(
        "User",
        foreign_keys=[assigned_doctor_id],
    )


class AppointmentProcedure(Base, BaseMixin):
    """Planned/intended treatment during booking"""
    __tablename__ = "appointment_procedures"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    procedure_catalog_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("procedure_catalogs.id", ondelete="RESTRICT"),
        nullable=False,
    )

    #
    # Optional tooth selection
    # Example:
    # [11,12]
    #
    tooth_numbers: Mapped[list[int] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Estimated pricing at booking time
    estimated_cost: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    estimated_duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    # Receptionist / doctor notes
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[AppointmentProcedureStatusEnum] = mapped_column(
        Enum(
            AppointmentProcedureStatusEnum,
            name="appointment_procedure_status_enum",
        ),
        default=AppointmentProcedureStatusEnum.PLANNED,
    )

    # relationships
    appointment = relationship(
        "Appointment",
        back_populates="planned_procedures",
    )
    procedures = relationship(
        "Procedure",
        back_populates="appointment_procedure",
    )
    procedure_catalog = relationship(
        "ProcedureCatalog",
        back_populates="appointment_procedures",
    )
    
    __table_args__ = (
        UniqueConstraint(
            "appointment_id",
            "procedure_catalog_id",
            name="uq_appointment_planned_procedure",
        ),
    )
