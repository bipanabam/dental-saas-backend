from datetime import date
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BaseMixin
from app.utils.enums import GenderEnum, BloodGroupEnum, PatientCategoryEnum, PatientStatusEnum, FamilyRelationshipEnum

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
    family_links = relationship(
        "PatientFamilyLink",
        foreign_keys="PatientFamilyLink.primary_patient_id",
        back_populates="primary_patient",
        cascade="all, delete-orphan",
    )

    linked_to = relationship(
        "PatientFamilyLink",
        foreign_keys="PatientFamilyLink.family_member_id",
        back_populates="family_member",
    )
    appointments = relationship(
        "Appointment",
        back_populates="patient",
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
        ),
    )
    
class PatientFamilyLink(Base, BaseMixin):
    __tablename__ = "patient_family_links"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    primary_patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
    )

    family_member_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
    )

    relationship_type: Mapped[FamilyRelationshipEnum] = mapped_column(
        Enum(FamilyRelationshipEnum, name="family_relationship_enum"),
        nullable=False,
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
    primary_patient = relationship(
        "Patient",
        foreign_keys=[primary_patient_id],
        back_populates="family_links",
    )

    family_member = relationship(
        "Patient",
        foreign_keys=[family_member_id],
        back_populates="linked_to",
    )
    
    __table_args__ = (
    UniqueConstraint(
        "primary_patient_id",
        "family_member_id",
        name="uq_patient_family_link"
    ),
)