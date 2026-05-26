from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.enums import ProcedureCategoryEnum
from app.models.procedure import ProcedureCatalog

DEFAULT_PROCEDURES = [
    {
        "code": "CONSULTATION",
        "name": "Consultation",
        "category": ProcedureCategoryEnum.DIAGNOSTIC,
        "duration": 15,
        "cost": 500,
    },
    {
        "code": "CLEANING",
        "name": "Teeth Cleaning",
        "category": ProcedureCategoryEnum.PREVENTIVE,
        "duration": 30,
        "cost": 2000,
    },
    {
        "code": "FILLING",
        "name": "Dental Filling",
        "category": ProcedureCategoryEnum.RESTORATIVE,
        "duration": 45,
        "cost": 3500,
    },
    {
        "code": "RCT",
        "name": "Root Canal Treatment",
        "category": ProcedureCategoryEnum.ENDODONTIC,
        "duration": 90,
        "cost": 12000,
    },
    {
        "code": "EXTRACTION",
        "name": "Tooth Extraction",
        "category": ProcedureCategoryEnum.SURGICAL,
        "duration": 45,
        "cost": 5000,
    },
    {
        "code": "WHITENING",
        "name": "Teeth Whitening",
        "category": ProcedureCategoryEnum.COSMETIC,
        "duration": 60,
        "cost": 15000,
    },
]

async def seed_default_procedures(db: AsyncSession):

    for procedure_data in DEFAULT_PROCEDURES:

        result = await db.execute(
            select(ProcedureCatalog).where(
                ProcedureCatalog.code == procedure_data["code"],
                ProcedureCatalog.tenant_id.is_(None),
            )
        )

        existing = result.scalar_one_or_none()

        if existing:
            continue

        procedure = ProcedureCatalog(
            tenant_id=None,
            code=procedure_data["code"],
            name=procedure_data["name"],
            category=procedure_data["category"],
            default_duration_minutes=procedure_data["duration"],
            default_cost=procedure_data["cost"],
            is_active=True,
        )

        db.add(procedure)

    await db.commit()

    print("Default procedures seeded.")