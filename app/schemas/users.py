
from pydantic import BaseModel, field_validator
import uuid

from pydantic import BaseModel, EmailStr, ConfigDict

class TenantSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    
class MembershipSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant: TenantSummary
    role: str
    is_active: bool

class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID

    email: EmailStr
    username: str

    phone_number: str | None = None

    is_active: bool
    is_verified: bool

class UserListItem(UserBase):
    role: str
    
class UserDetail(UserBase):
    memberships: list[MembershipSummary]
    permissions: list[str]

class CurrentUserResponse(UserBase):
    tenant: TenantSummary
    role: str
    permissions: list[str]
    
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    phone_number: str | None = None
    role: str  # role name to assign to the user
    
class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = None
    phone_number: str | None = None
    role: str | None = None
    is_active: bool | None = None
    is_verified: bool | None = None
    
    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v):
        if v is None:
            return v
        # Add phone number validation logic here
        if not v.isdigit():
            raise ValueError("Phone number must contain only digits")
        if len(v) < 7 or len(v) > 15:
            raise ValueError("Phone number must be between 7 and 15 digits")
        return v