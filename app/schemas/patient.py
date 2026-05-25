from datetime import date
from pydantic import BaseModel, EmailStr, field_validator, field_validator

from app.utils.enums import GenderEnum, BloodGroupEnum, PatientCategoryEnum


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

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        try:
            EmailStr(v)
        except ValueError:
            raise ValueError("Invalid email format")
        return v

class PatientResponse(BaseModel):
    # id: str
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
    allergies: str | None
    status: str | None
    
    visit_count: int
    last_visit_at: str | None
    
    created_by_id: str | None
    updated_by_id: str | None

    class Config:
        from_attributes = True