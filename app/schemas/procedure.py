from uuid import UUID

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