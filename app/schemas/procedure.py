from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.utils.enums import (
    ProcedureCategoryEnum
)

class ProcedureCatalogMini(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    name: str
    code: str | None
    category: ProcedureCategoryEnum
    
    
class ProcedureUpdate(BaseModel):
    description: str | None = None
    final_cost: float | None = None
    performed_duration_minutes: int | None = None
    
    
class ProcedureOut(BaseModel):

    id: UUID
    encounter_id: UUID
    patient_id: UUID

    procedure_catalog_id: UUID
    procedure_name: str | None
    tooth_numbers: list[int] | None
    
    status: str
    
    estimated_cost: float | None
    final_cost: float | None
    
    description: str | None
    performed_by_id: UUID
    
    performed_duration_minutes: int | None = None
    
    procedure_date: datetime | None
    completed_at: datetime | None


class ProcedureCreate(BaseModel):
    procedure_catalog_id: UUID
    tooth_numbers: list[int] | None = None
    description: str | None = None
    estimated_cost: float | None = None
    final_cost: float | None = None
    performed_duration_minutes: int | None = None