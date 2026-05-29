from typing import Annotated
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.core.dependencies.auth import CurrentAuth
from app.core.dependencies.permissions import (
    CanReadAppointments,
    CanCreateAppointments,
    CanUpdateAppointments,
    CanDeleteAppointments,
    CanCheckInAppointments,
    CanCompleteAppointments
)

from app.services.appointment import AppointmentService, AppointmentWorkflowService

from app.schemas.appointment import (
    AppointmentListResponse,
    AppointmentFilter,
    AppointmentCreate,
    AppointmentCreateWalkIn,
    AppointmentListItem,
    AppointmentDetail,
    AppointmentUpdate,
    AppointmentCancel,
    AppointmentReschedule,
    AppointmentFollowUpCreate,
    AppointmentCheckInResponse,
    TodaysAppointmentListResponse
)

router = APIRouter(
    prefix="/appointments",
    tags=["appointments"],
)

# GET -> /appointments
@router.get("/", response_model=AppointmentListResponse)
async def list_appointments(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    filter: Annotated[
        AppointmentFilter,
        Depends()
    ],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _: None = CanReadAppointments,
):
    result =  await AppointmentService.list_appointments(
        db=db,
        tenant_id=auth.membership.tenant_id,
        filter=filter,
        skip=skip,
        limit=limit
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No appointments found"
        )
        
    return result

# GET -> /appointments/today
@router.get("/today", response_model=TodaysAppointmentListResponse)
async def list_todays_appointments(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _: None = CanReadAppointments,
):
    """Today's appointments with queue status"""
    result =  await AppointmentService.list_todays_appointments(
        db=db,
        tenant_id=auth.membership.tenant_id,
        skip=skip,
        limit=limit
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No appointments found for today"
        )
        
    return result

# POST -> /appointments
@router.post("/", response_model=AppointmentListItem, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    payload: AppointmentCreate,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanCreateAppointments,
) -> AppointmentListItem:
    """Create new appointment for patient"""

    return await AppointmentService.create_appointment(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.user.id,
        payload=payload
    )
    
    
# POST -> /appointments/walk-in
@router.post(
    "/walk-in", 
    response_model=AppointmentCheckInResponse, 
    status_code=status.HTTP_201_CREATED
)
async def walk_in_appointment(
    payload: AppointmentCreateWalkIn,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanCreateAppointments,
) -> AppointmentCheckInResponse:
    """Create new appointment for walk-in patient"""

    return await AppointmentService.walk_in_appointment(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.user.id,
        payload=payload
    )
    

# GET -> /appointments/{appointment_id}
@router.get("/{appointment_id}", response_model=AppointmentDetail)
async def get_appointment_detail(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    appointment_id: UUID,
    _: None = CanReadAppointments,
):
    """Get appointment detail with all the planned procedure"""
    return await AppointmentService.get_appointment_detail(
        db=db,
        tenant_id=auth.membership.tenant_id,
        appointment_id=appointment_id
    )

@router.put("/{appointment_id}", response_model=AppointmentListItem, status_code=status.HTTP_201_CREATED)
async def update_appointment(
    payload: AppointmentUpdate,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    appointment_id=UUID,
    _: None = CanUpdateAppointments,
) -> AppointmentListItem:
    """Update appointment for patient"""

    return await AppointmentService.update_appointment(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.user.id,
        appointment_id=appointment_id,
        payload=payload
    )
    
@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_appointment(
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    appointment_id: UUID,
    payload: AppointmentCancel,
    _: None = CanDeleteAppointments,
):
    """Cancel appointment for patient"""

    await AppointmentService.cancel_appointment(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.user.id,
        appointment_id=appointment_id,
        payload=payload
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Appointment WorkFlow
@router.post(
    "/{appointment_id}/confirm",
    response_model=AppointmentListItem,
)
async def confirm_appointment(
    appointment_id: UUID,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanUpdateAppointments,
):
    """Confirm booked appointment"""
    return await AppointmentWorkflowService.confirm_appointment(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.user.id,
        appointment_id=appointment_id,
    )
    
@router.post(
    "/{appointment_id}/check-in",
    response_model=AppointmentCheckInResponse,
)
async def check_in_appointment(
    appointment_id: UUID,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanCheckInAppointments,
):
    """Check-in for scheduled appointment with token in return"""
    return await AppointmentWorkflowService.check_in_appointment(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.user.id,
        appointment_id=appointment_id,
    )
    
@router.post(
    "/{appointment_id}/start",
    response_model=AppointmentListItem,
)
async def start_appointment(
    appointment_id: UUID,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanUpdateAppointments,
):
    """Start appointment with all the planned procedure it consists of"""
    return await AppointmentWorkflowService.start_appointment(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.user.id,
        appointment_id=appointment_id,
    )
    
@router.post(
    "/{appointment_id}/complete",
    response_model=AppointmentListItem,
)
async def complete_appointment(
    appointment_id: UUID,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanCompleteAppointments,
):
    """Set the given appointment as completed"""
    return await AppointmentWorkflowService.complete_appointment(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.user.id,
        appointment_id=appointment_id,
    )
    
@router.post(
    "/{appointment_id}/no-show",
    response_model=AppointmentListItem,
)
async def mark_no_show(
    appointment_id: UUID,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: None = CanUpdateAppointments,
):
    return await AppointmentWorkflowService.mark_no_show(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.user.id,
        appointment_id=appointment_id,
    )
    
    
@router.post(
    "/{appointment_id}/reschedule",
    response_model=AppointmentListItem,
)
async def reschedule_appointment(
    appointment_id: UUID,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: AppointmentReschedule,
    _: None = CanCreateAppointments,
):
    """Reschedule appointment with updated doctor and appointment_date"""
    return await AppointmentWorkflowService.reschedule_appointment(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.user.id,
        appointment_id=appointment_id,
        payload=payload
    )
    
    
@router.post(
    "/{appointment_id}/follow-up",
    response_model=AppointmentListItem,
)
async def create_follow_up(
    appointment_id: UUID,
    auth: CurrentAuth,
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: AppointmentFollowUpCreate,
    _: None = CanCreateAppointments,
):
    """create follow up for previous appointment"""
    return await AppointmentWorkflowService.create_follow_up(
        db=db,
        tenant_id=auth.membership.tenant_id,
        user_id=auth.user.id,
        appointment_id=appointment_id,
        payload=payload
    )
    