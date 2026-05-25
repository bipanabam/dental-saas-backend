import uuid

from sqlalchemy import (
    String,
    ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BaseMixin


class MedicalRecord(Base, BaseMixin):
    __tablename__ = "medical_records"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    primary_doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    ) # primary doctor assigned to this patient
    
    emergency_contact_name: Mapped[str | None] = mapped_column(String(255))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(20))

    insurance_provider: Mapped[str | None] = mapped_column(String(255))
    insurance_number: Mapped[str | None] = mapped_column(String(100))

    systemic_conditions: Mapped[str | None] = mapped_column(String(500))
    current_medications: Mapped[str | None] = mapped_column(String(500))
    prior_surgeries: Mapped[str | None] = mapped_column(String(500))
    allergies: Mapped[str | None] = mapped_column(String(500))

    title: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str | None] = mapped_column(String(50))

    patient = relationship(
        "Patient",
        back_populates="medical_record",
    )