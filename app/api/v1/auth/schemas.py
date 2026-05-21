import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class TenantBase(BaseModel):
    name: str = Field(title="Name of the company or organization...")
    slug: str


class TenantPublic(TenantBase):

    model_config = ConfigDict(from_attributes=True)

    plan: str  # basic,pro,enterprise
    status: str  # trial,active,cancelled


class TenantPrivate(TenantPublic):
    id: uuid.UUID
    email: EmailStr


class Register(BaseModel):
    email: EmailStr
    password: str
    name: str = Field(title="Name of the company or organization")  # Acme Corp
    slug: str  # "acme" becomes the subdomain

    @field_validator("slug")
    @classmethod
    def slug_must_be_lowercase_alphanumeric(cls, v: str) -> str:
        import re

        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError(
                "Slug must be lowercase letters, numbers, and hyphens only"
            )
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

class RegisterTenantResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    tenant_id: uuid.UUID

    tenant_name: str
    tenant_slug: str

    owner_email: EmailStr

    subscription_plan: str
    subscription_status: str

class Login(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):

    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    expires_in: int
class RefreshIn(BaseModel):
    refresh_token: str

class UserBase(BaseModel):
    username: str
    email: EmailStr
    
class UserMe(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID

    email: EmailStr
    username: str

    phone_number: str | None = None

    is_active: bool
    is_verified: bool
    
class TenantSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    
class MembershipSummary(BaseModel):
    tenant: TenantSummary
    role: str
    
class MeResponse(UserMe):
    memberships: list[MembershipSummary]
    permissions: list[str]