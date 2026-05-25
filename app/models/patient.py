from datetime import date
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BaseMixin
from app.utils.enums import GenderEnum, BloodGroupEnum, PatientCategoryEnum, PatientStatusEnum, FamilyRelationEnum

class Patient(Base, BaseMixin):
    __tablename__ = "patients"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    patient_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    ) # unique per tenant, auto-generated e.g. BDC-00123
    
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    date_of_birth: Mapped[date] = mapped_column(nullable=True)
    gender: Mapped[GenderEnum] = mapped_column( 
        Enum(GenderEnum, name="gender_enum"),
        default=GenderEnum.OTHER
    )
    blood_group: Mapped[BloodGroupEnum] = mapped_column(
        Enum(BloodGroupEnum, name="blood_group_enum"),
        default=None
    )
    
    phone: Mapped[str] = mapped_column(String(20), nullable=False) # unique per tenant
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    address: Mapped[str] = mapped_column(String(500), nullable=True)
    
    status: Mapped[PatientStatusEnum] = mapped_column(
        Enum(PatientStatusEnum, name="patient_status_enum"),
        default=PatientStatusEnum.ACTIVE
    )
    category: Mapped[PatientCategoryEnum] = mapped_column(
        Enum(PatientCategoryEnum, name="patient_category_enum"),
        default=PatientCategoryEnum.REGULAR
    )
    
    visit_count: Mapped[int] = mapped_column(Integer, default=0)
    last_visit_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    primary_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patients.id", ondelete="SET NULL"),
    )
    family_relation: Mapped[FamilyRelationEnum | None] = mapped_column(
        Enum(FamilyRelationEnum, name="family_relation_enum")
    )
    
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # relationships
    medical_record = relationship(
        "MedicalRecord",
        back_populates="patient",
        uselist=False,
        cascade="all, delete-orphan",
    )

    primary_account = relationship(
        "Patient",
        remote_side="Patient.id",
        backref="family_members",
    )
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "patient_code",
            name="uq_patient_code_per_tenant"
        ),
        UniqueConstraint(
            "tenant_id",
            "phone",
            name="uq_patient_phone_per_tenant"
        ),
        Index(
            "idx_patient_search",
            "first_name",
            "last_name",
            "phone",
            "email",
            unique=True,
        ),
    )