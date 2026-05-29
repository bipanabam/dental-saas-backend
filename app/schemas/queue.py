from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.utils.enums import ( 
    QueueStatusEnum, 
    AppointmentStatusEnum, 
    AppointmentTypeEnum,
    AppointmentSourceEnum
    )

class QueueItem(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )
    
    id: UUID
    token_number: int
    status: QueueStatusEnum

    priority: int
    
    called_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    estimated_wait_mins: int | None
    
    
class PatientMini(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    patient_code: str

    first_name: str
    last_name: str

    phone: str | None
    
class DoctorMini(BaseModel):
    model_config = ConfigDict(
    from_attributes=True
    )

    id: UUID

    username: str
    
class AppointmentMini(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID

    patient: PatientMini

    doctor: DoctorMini | None = None

    appointment_type: AppointmentTypeEnum
    duration_minutes: int

    chief_complaint: str | None

    source: AppointmentSourceEnum
    status: AppointmentStatusEnum
    
class TodaysQueueListItem(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    queue: QueueItem
    appointment: AppointmentMini


class TodaysQueueListResponse(BaseModel):
    items: list[TodaysQueueListItem]
    total: int
    skip: int
    limit: int
    
class DoctorQueueListItem(BaseModel):
    queue_id: UUID
    token_number: int
    status: QueueStatusEnum

    patient: PatientMini

    appointment_id: UUID
    appointment_status: AppointmentStatusEnum
    appointment_type: AppointmentTypeEnum

    chief_complaint: str | None
    
class DoctorQueueListResponse(BaseModel):
    items: list[DoctorQueueListItem]
    total: int
    skip: int
    limit: int
    
class QueueActionResponse(BaseModel):
    success: bool
    message: str
    item: DoctorQueueListItem
    
class QueueWaitEstimateResponse(BaseModel):
    token_number: int
    patients_ahead: int
    estimated_wait_mins: int
    
class PublicQueueDisplayItem(BaseModel):
    token_number: int
    doctor_name: str | None
    status: QueueStatusEnum


class PublicQueueDisplayResponse(BaseModel):
    now_serving: list[PublicQueueDisplayItem]
    waiting: list[PublicQueueDisplayItem]