from datetime import datetime, date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import (
    AppointmentTypeEnum,
    AppointmentStatusEnum,
    AppointmentSourceEnum,
    AppointmentCancellationReasonEnum,
    AppointmentProcedureStatusEnum,
    PaymentStatusEnum,
    QueueStatusEnum
)

from app.schemas.procedure import ProcedureCatalogMini


class AppointmentProcedureBase(BaseModel):
    tooth_numbers: list[int] | None = None
    estimated_cost: float | None = None
    estimated_duration_minutes: int | None = None
    notes: str | None = None
    procedure_catalog_id: UUID


class AppointmentProcedureCreate(AppointmentProcedureBase):
    pass


class AppointmentProcedureResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    tooth_numbers: list[int] | None = None
    estimated_cost: float | None = None
    estimated_duration_minutes: int | None = None
    notes: str | None = None
    status: AppointmentProcedureStatusEnum
    
    procedure_catalog_id: UUID
    procedure_catalog: (
        ProcedureCatalogMini | None
    )


class AppointmentCreate(BaseModel):
    patient_id: UUID
    doctor_id: UUID | None = None

    appointment_type: AppointmentTypeEnum = (
        AppointmentTypeEnum.BOOKED
    )

    appointment_date: datetime
    duration_minutes: int = 30

    chief_complaint: str | None = None
    notes: str | None = None

    source: AppointmentSourceEnum = (
        AppointmentSourceEnum.FRONT_DESK
    )

    procedures: list[AppointmentProcedureCreate] = Field(
        default_factory=list
    )
    

class AppointmentCreateWalkIn(BaseModel):
    patient_id: UUID
    doctor_id: UUID | None = None
    duration_minutes: int = 30
    chief_complaint: str | None = None
    notes: str | None = None
    source: AppointmentSourceEnum = (
        AppointmentSourceEnum.FRONT_DESK
    )
    procedures: list[AppointmentProcedureCreate] = Field(
        default_factory=list
    )

class AppointmentUpdate(BaseModel):
    doctor_id: UUID | None = None

    appointment_date: datetime | None = None
    duration_minutes: int | None = None

    chief_complaint: str | None = None
    notes: str | None = None

    status: AppointmentStatusEnum | None = None

    payment_status: PaymentStatusEnum | None = None

    cancellation_reason: str | None = None
    
    procedures: list[AppointmentProcedureCreate] | None = None


class AppointmentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    patient_id: UUID
    assigned_doctor_id: UUID | None

    appointment_date: datetime

    appointment_type: AppointmentTypeEnum
    status: AppointmentStatusEnum
    payment_status: PaymentStatusEnum

    chief_complaint: str | None
    
    source: AppointmentSourceEnum

    created_at: datetime


class AppointmentDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    patient_id: UUID
    assigned_doctor_id: UUID | None

    appointment_type: AppointmentTypeEnum
    appointment_date: datetime
    duration_minutes: int

    chief_complaint: str | None
    notes: str | None

    source: AppointmentSourceEnum

    status: AppointmentStatusEnum
    payment_status: PaymentStatusEnum

    cancellation_reason: str | None

    procedures: list[AppointmentProcedureResponse]
    
    created_by: str | None

    created_at: datetime
    updated_at: datetime


class AppointmentFilter(BaseModel):
    date_range: date | None = None
    doctor_id: UUID | None = None
    status: AppointmentStatusEnum | None = None
    appointment_type: AppointmentTypeEnum | None = None
    source: AppointmentSourceEnum | None = None

class AppointmentListResponse(BaseModel):
    items: list[AppointmentListItem]
    total: int
    skip: int
    limit: int
    
class AppointmentCancel(BaseModel):
    cancellation_reason_type: (
        AppointmentCancellationReasonEnum
    )
    cancellation_reason_note: str | None = None
    
class AppointmentCheckInResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    appointment: AppointmentListItem

    token_number: int

    queue_id: UUID

    queue_status: QueueStatusEnum
    
class AppointmentReschedule(BaseModel):
    appointment_date: datetime
    assigned_doctor_id: UUID | None = None
    notes: str | None = None


class AppointmentFollowUpCreate(BaseModel):
    appointment_date: datetime
    assigned_doctor_id: UUID | None = None

    chief_complaint: str | None = None
    notes: str | None = None