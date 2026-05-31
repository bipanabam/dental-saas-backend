from typing import Annotated
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.core.dependencies.auth import CurrentAuth
# from app.core.dependencies.permissions import (
#    CanReadQueue,
#    CanCreateQueue,
#    CanUpdateQueue,
#    CanDeleteQueue
# )

from app.services.queue import QueueService
from app.schemas.queue import (
    TodaysQueueListResponse, 
    DoctorQueueListResponse,
    QueueActionResponse,
    QueueWaitEstimateResponse
    )

router = APIRouter(
    prefix="/queue",
    tags=["Queue"],
)

# GET -> /queue/today
@router.get("/today", response_model=TodaysQueueListResponse)
async def list_todays_queue(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    # _: None = CanReadQueue,
):
    """Live queue for today (all doctors)"""
    return await QueueService.list_todays_queue(
        db=db,
        tenant_id=auth.membership.tenant_id,
        skip=skip,
        limit=limit
    )
    
# GET -> /queue/doctors/{doctor_id}/today
@router.get("/doctors/{doctor_id}/today", response_model=DoctorQueueListResponse)
async def get_queue_for_doctor(
    doctor_id: UUID,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    # _: None = CanReadQueue,
):
    """Live queue for specific doctor"""
    return await QueueService.get_queue_for_doctor(
        db=db,
        tenant_id=auth.membership.tenant_id,
        doctor_id=doctor_id,
        skip=skip,
        limit=limit
    )
    
# POST -> /queue/{queue_id}/call
@router.post(
    "/{queue_id}/call",
    response_model=QueueActionResponse,
)
async def call_for_next_patient(
    queue_id: UUID,
    auth: CurrentAuth,
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
):
    """Call patient to chair"""

    return await QueueService.call_for_next_patient(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.membership.user_id,
        queue_id=queue_id,
    )


# POST -> /queue/{queue_id}/skip
@router.post(
    "/{queue_id}/skip",
    response_model=QueueActionResponse,
)
async def skip_the_token(
    queue_id: UUID,
    auth: CurrentAuth,
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
):
    """Skip queue token"""

    return await QueueService.skip_the_token(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.membership.user_id,
        queue_id=queue_id,
    )


# POST -> /queue/{queue_id}/recall
@router.post(
    "/{queue_id}/recall",
    response_model=QueueActionResponse,
)
async def recall_skipped_token(
    queue_id: UUID,
    auth: CurrentAuth,
    db: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
):
    """Recall skipped queue token"""

    return await QueueService.recall_skipped_token(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.membership.user_id,
        queue_id=queue_id,
    )
    
# GET -> /queue/{queue_id}/estimated-wait
@router.get(
    "/{queue_id}/estimated-wait",
    response_model=QueueWaitEstimateResponse,
)
async def get_estimated_wait(
    queue_id: UUID,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Estimated wait time for a queue token"""

    return await QueueService.get_estimated_wait_for_token(
        db=db,
        tenant_id=auth.membership.tenant_id,
        queue_id=queue_id,
    )
    
# GET -> /queue/display
@router.get("/display")
async def get_public_display_for_tokens(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Public display endpoint (no auth, for TV screen)"""
    return await QueueService.get_public_display_for_tokens(
        db=db,
        tenant_id=auth.membership.tenant_id
    )