from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies.auth import CurrentAuth
from app.core.database  import get_db

from app.services.procedure import ProcedureService, ProcedureCancellationService

from app.schemas.procedure import ProcedureOut, ProcedureUpdate, ProcedureCreate

router = APIRouter(prefix="/procedures", tags=["Procedures"])


@router.get(
    "/procedures/{procedure_id}",
    response_model=ProcedureOut,
)
async def get_procedure(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    procedure_id: UUID,
):
    return await ProcedureService.get(
        db=db,
        tenant_id=auth.membership.tenant_id,
        procedure_id=procedure_id,
    )
    
    
@router.patch(
    "/procedures/{procedure_id}",
    response_model=ProcedureOut,
)
async def update_procedure(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    procedure_id: UUID,
    payload: ProcedureUpdate,
):
    return await ProcedureService.update(
        db=db,
        tenant_id=auth.membership.tenant_id,
        procedure_id=procedure_id,
        payload=payload,
    )
    

@router.post(
    "/procedures/{procedure_id}/cancel",
    response_model=ProcedureOut,
)
async def cancel_procedure(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    procedure_id: UUID,
):
    return await ProcedureCancellationService.cancel(
        db=db,
        tenant_id=auth.membership.tenant_id,
        procedure_id=procedure_id,
    )
