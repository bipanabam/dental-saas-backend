from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.core.dependencies.auth import CurrentAuth
from app.core.dependencies.permissions import (
    CanReadAppointments,
    CanCreateAppointments,
    CanUpdateAppointments
)

from app.api.v1.appointments.services import AppointmentService
from app.utils.enums import AppointmentStatusEnum

from app.schemas.appointment import (
    AppointmentListResponse,
    AppointmentCreate,
    AppointmentListItem,
    AppointmentDetail,
    AppointmentUpdate
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
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    date_range: str | None = None,
    appointment_status: AppointmentStatusEnum | None = None,
    doctor_id: UUID | None = None,
    _: None = CanReadAppointments,
):
    result =  await AppointmentService.list_appointments(
        db=db,
        tenant_id=auth.membership.tenant_id,
        date_range=date_range,
        appointment_status=appointment_status,
        doctor_id=doctor_id,
        skip=skip,
        limit=limit
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No patients found for this tenant"
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
    

# GET -> /appointments/{appointment_id}
@router.get("/appointments/{appointment_id}", response_model=AppointmentDetail)
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

@router.put("/appointments/{appointment_id}", response_model=AppointmentListItem, status_code=status.HTTP_201_CREATED)
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