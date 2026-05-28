from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, field_validator

from app.utils.enums import (
    GenderEnum, 
    BloodGroupEnum, 
    PatientCategoryEnum, 
    PatientStatusEnum,
    FamilyRelationshipEnum
)

class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    gender: GenderEnum = GenderEnum.OTHER
    blood_group: BloodGroupEnum | None = None
    phone: str
    email: EmailStr | None = None
    address: str | None = None
    
    category: PatientCategoryEnum = PatientCategoryEnum.REGULAR
    allergies: str | None = None
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        import re

        if not re.match(r"^\+?[0-9\s\-]+$", v):
            raise ValueError("Phone number must contain only digits, spaces, dashes, and an optional leading +")
        if len(re.sub(r"[\s\-]", "", v)) < 10:
            raise ValueError("Phone number must be at least 10 digits long")
        return v
    
class PatientUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None   
    gender: GenderEnum | None = None
    blood_group: BloodGroupEnum | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    category: PatientCategoryEnum | None = None
    status: str | None = None
    
    last_visit_at: date | None = None
    visit_count: int | None = None
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        import re

        if not re.match(r"^\+?[0-9\s\-]+$", v):
            raise ValueError("Phone number must contain only digits, spaces, dashes, and an optional leading +")
        if len(re.sub(r"[\s\-]", "", v)) < 10:
            raise ValueError("Phone number must be at least 10 digits long")
        return v

class PatientBase(BaseModel):
    id: UUID
    patient_code: str
    first_name: str
    last_name: str | None
    phone: str
    email: str | None
    address: str | None
    date_of_birth: date | None
    gender: GenderEnum
    blood_group: BloodGroupEnum | None
    category: PatientCategoryEnum
    status: PatientStatusEnum | None  
    
class PatientResponse(PatientBase):
    model_config = ConfigDict(from_attributes=True)
    
    visit_count: int
    last_visit_at: datetime | None
    
    # created_by_id: str | None
    # updated_by_id: str | None
        
class PatientListItem(PatientBase):
    model_config = ConfigDict(from_attributes=True)
    
    pass

class PatientListResponse(BaseModel):
    items: list[PatientListItem]
    total: int
    skip: int
    limit: int

class PatientFilter(BaseModel):
    category: PatientCategoryEnum | None = None
    status: PatientStatusEnum | None = None
    gender: GenderEnum | None = None
    blood_group: BloodGroupEnum | None = None

class PatientSearchResult(PatientListItem):
    pass

class MedicalRecordSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
     
    id: UUID
    patient_id: UUID
    primary_doctor_id: UUID | None
    allergies: str | None
    systemic_conditions: str | None
    current_medications: str | None
    prior_surgeries: str | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None 
    
class MedicalRecordPayload(BaseModel):
    allergies: str | None = None
    systemic_conditions: str | None = None
    current_medications: str | None = None
    prior_surgeries: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    
    @field_validator("emergency_contact_phone")
    @classmethod
    def validate_emergency_contact_phone(cls, v: str) -> str:
        import re

        if not re.match(r"^\+?[0-9\s\-]+$", v):
            raise ValueError("Phone number must contain only digits, spaces, dashes, and an optional leading +")
        if len(re.sub(r"[\s\-]", "", v)) < 10:
            raise ValueError("Phone number must be at least 10 digits long")
        return v
    
class PatientDetail(PatientBase):
    model_config = ConfigDict(from_attributes=True)
     
    visit_count: int
    last_visit_at: datetime | None
    
    medical_record: MedicalRecordSummary | None
   
    created_by_id: UUID | None
    updated_by_id: UUID | None
    created_at: datetime
    updated_at: datetime
    
   
class FamilyBase(BaseModel):
    id: UUID
    first_name: str
    last_name: str | None
    relationship_type: FamilyRelationshipEnum | None 
    
class FamilyListItem(FamilyBase):
    pass

class FamilyLinkCreate(BaseModel):
    # primary_account_id: UUID
    family_member_id: UUID
    relationship_type: FamilyRelationshipEnum | None