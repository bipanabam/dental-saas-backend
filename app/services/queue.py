from uuid import UUID
from datetime import datetime, UTC, date

from fastapi import HTTPException, status
from sqlalchemy import select, func, case
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.queue import Queue
from app.models.appointment import Appointment
from app.models.user import User, Membership, Role

from app.services.appointment import AppointmentWorkflowService
from app.services.shared.services import SharedService

from app.schemas.queue import (
    TodaysQueueListItem,
    TodaysQueueListResponse,
    AppointmentMini,
    QueueItem,
    DoctorQueueListResponse,
    DoctorQueueListItem,
    PatientMini,
    QueueActionResponse,
    QueueWaitEstimateResponse,
    PublicQueueDisplayResponse,
    PublicQueueDisplayItem
)

from app.utils.enums import (
    QueueStatusEnum,
    RoleEnum
)

class QueueService:
    
    @staticmethod
    async def _get_queue_or_404(
        db: AsyncSession,
        tenant_id: UUID,
        queue_id: UUID,
    ) -> Queue:

        query = (
            select(Queue)
            .where(
                Queue.id == queue_id,
                Queue.tenant_id == tenant_id,
            )
            .options(
                joinedload(Queue.appointment)
                .joinedload(Appointment.patient),

                joinedload(Queue.appointment)
                .joinedload(Appointment.doctor),
            )
        )

        result = await db.execute(query)

        queue = result.scalar_one_or_none()

        if not queue:
            raise HTTPException(
                status_code=404,
                detail="Queue entry not found",
            )

        return queue
    
    @staticmethod
    def _build_queue_response_item(
        queue: Queue,
    ) -> DoctorQueueListItem:

        appointment = queue.appointment

        return DoctorQueueListItem(
            queue_id=queue.id,
            token_number=queue.token_number,
            status=queue.status,

            patient=PatientMini.model_validate(
                appointment.patient
            ),

            appointment_id=appointment.id,
            appointment_status=appointment.status,
            appointment_type=appointment.appointment_type,

            chief_complaint=appointment.chief_complaint,
        )
    
    @staticmethod
    async def _ensure_no_active_queue(
        db: AsyncSession,
        tenant_id: UUID,
        doctor_id: UUID | None,
    ) -> None:
        """
        Ensure doctor does not already have
        an active queue in progress.
        """

        if not doctor_id:
            return

        today = datetime.now(UTC).date()

        result = await db.execute(
            select(Queue.id)
            .where(
                Queue.tenant_id == tenant_id,
                Queue.doctor_id == doctor_id,
                Queue.queue_date == today,
                Queue.status == QueueStatusEnum.IN_PROGRESS,
            )
            .limit(1)
        )

        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Doctor already has an active patient in progress"
                ),
            )

    @staticmethod
    async def list_todays_queue(
    db: AsyncSession,
    tenant_id: UUID,
    skip: int = 0,
    limit: int = 20,
    ) -> TodaysQueueListResponse:
        """
        Live queue for today.
        """

        today = datetime.now(UTC).date()

        filters = [
            Queue.tenant_id == tenant_id,
            Queue.queue_date == today,

            Queue.status.in_([
                QueueStatusEnum.WAITING,
                QueueStatusEnum.IN_PROGRESS,
                QueueStatusEnum.SKIPPED
            ])
        ]

        total_query = (
            select(func.count(Queue.id))
            .where(*filters)
        )

        total_result = await db.execute(
            total_query
        )

        total = total_result.scalar() or 0

        query = (
            select(Queue)
            .where(*filters)
            .options(
            joinedload(Queue.appointment).options(
                joinedload(Appointment.patient),
                joinedload(Appointment.doctor),
            ))
            .order_by(
                case(
                    (Queue.status == QueueStatusEnum.IN_PROGRESS, 0),
                    (Queue.status == QueueStatusEnum.WAITING, 1),
                    (Queue.status == QueueStatusEnum.SKIPPED, 2),
                    else_=2,
                ),
                Queue.token_number.asc(),
            )
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(query)

        queues = (
            result.scalars()
            .unique()
            .all()
        )

        return TodaysQueueListResponse(
            items=[
                TodaysQueueListItem(
                    queue=QueueItem.model_validate(queue),
                    appointment=AppointmentMini.model_validate(
                        queue.appointment
                    ),
                )
                for queue in queues
            ],

            total=total,
            skip=skip,
            limit=limit,
        )
        
    @staticmethod
    async def get_queue_for_doctor(
    db: AsyncSession,
    tenant_id: UUID,
    doctor_id: UUID,
    skip: int = 0,
    limit: int = 20,
    ) -> DoctorQueueListResponse:
        """
        Live queue for specific doctor
        """
        await SharedService._validate_doctor(
            db=db,
            tenant_id=tenant_id,
            doctor_id=doctor_id
        )
        today = datetime.now(UTC).date()

        filters = [
            Queue.tenant_id == tenant_id,
            Queue.queue_date == today,
            Queue.doctor_id == doctor_id,

            Queue.status.in_([
                QueueStatusEnum.WAITING,
                QueueStatusEnum.IN_PROGRESS,
            ])
        ]

        total_query = (
            select(func.count(Queue.id))
            .where(*filters)
        )

        total_result = await db.execute(
            total_query
        )

        total = total_result.scalar() or 0

        query = (
            select(Queue)
            .where(*filters)
            .options(
                joinedload(Queue.appointment).options(
                joinedload(Appointment.patient),
                joinedload(Appointment.doctor),
            ))
            .order_by(
                case(
                    (Queue.status == QueueStatusEnum.IN_PROGRESS, 0),
                    (Queue.status == QueueStatusEnum.WAITING, 1),
                    else_=2,
                ),
                Queue.token_number.asc(),
            )
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(query)

        queues = (
            result.scalars()
            .unique()
            .all()
        )
        
        return DoctorQueueListResponse(
            items=[
                DoctorQueueListItem(
                    queue_id=queue.id,
                    token_number=queue.token_number,
                    status=queue.status,

                    patient=PatientMini(
                        id= queue.appointment.patient.id,
                        patient_code=queue.appointment.patient.patient_code,
                        first_name=queue.appointment.patient.first_name,
                        last_name=queue.appointment.patient.last_name,
                        phone=queue.appointment.patient.phone
                    ),

                    appointment_id=queue.appointment.id,
                    appointment_status=queue.appointment.status,
                    appointment_type=queue.appointment.appointment_type,

                    chief_complaint=queue.appointment.chief_complaint,
                )
                for queue in queues
            ],

            total=total,
            skip=skip,
            limit=limit,
        )
        
    @staticmethod
    async def call_for_next_patient(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        queue_id: UUID,
    ) -> QueueActionResponse:

        queue = await QueueService._get_queue_or_404(
            db=db,
            tenant_id=tenant_id,
            queue_id=queue_id,
        )

        appointment = queue.appointment

        if queue.status != QueueStatusEnum.WAITING:
            raise HTTPException(
                status_code=400,
                detail="Only waiting tokens can be called",
            )

        await QueueService._ensure_no_active_queue(
            db=db,
            tenant_id=tenant_id,
            doctor_id=queue.doctor_id,
        )

        appointment = await (
            AppointmentWorkflowService
            .start_appointment(
                db=db,
                tenant_id=tenant_id,
                user_id=user_id,
                appointment_id=appointment.id,
            )
        )

        # reload fresh queue state
        queue = await QueueService._get_queue_or_404(
            db=db,
            tenant_id=tenant_id,
            queue_id=queue_id,
        )


        return QueueActionResponse(
            success=True,
            message="Patient called successfully",
            item=QueueService._build_queue_response_item(
                queue
            ),
        )
                
    @staticmethod
    async def skip_the_token(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        queue_id: UUID,
    ) -> QueueActionResponse:

        queue = await QueueService._get_queue_or_404(
            db=db,
            tenant_id=tenant_id,
            queue_id=queue_id,
        )

        if queue.status != QueueStatusEnum.WAITING:
            raise HTTPException(
                status_code=400,
                detail="Only waiting tokens can be skipped",
            )

        queue.status = QueueStatusEnum.SKIPPED
        queue.appointment.updated_by_id = user_id

        try:
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()

            raise HTTPException(
                status_code=500,
                detail="Failed to skip token",
            )

        await db.refresh(queue)

        return QueueActionResponse(
            success=True,
            message="Token skipped successfully",
            item=QueueService._build_queue_response_item(
                queue
            ),
        )
        
    @staticmethod
    async def recall_skipped_token(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        queue_id: UUID,
    ) -> QueueActionResponse:

        queue = await QueueService._get_queue_or_404(
            db=db,
            tenant_id=tenant_id,
            queue_id=queue_id,
        )

        if queue.status != QueueStatusEnum.SKIPPED:
            raise HTTPException(
                status_code=400,
                detail="Only skipped tokens can be recalled",
            )
            
        await QueueService._ensure_no_active_queue(
            db=db,
            tenant_id=tenant_id,
            doctor_id=queue.doctor_id,
        )

        queue.status = QueueStatusEnum.WAITING
        queue.appointment.updated_by_id = user_id

        try:
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()

            raise HTTPException(
                status_code=500,
                detail="Failed to recall token",
            )

        await db.refresh(queue)

        return QueueActionResponse(
            success=True,
            message="Skipped token recalled successfully",
            item=QueueService._build_queue_response_item(
                queue
            ),
        )
        
    @staticmethod
    async def get_estimated_wait_for_token(
        db: AsyncSession,
        tenant_id: UUID,
        queue_id: UUID,
    ) -> QueueWaitEstimateResponse:

        today = datetime.now(UTC).date()

        queue = await QueueService._get_queue_or_404(
            db=db,
            tenant_id=tenant_id,
            queue_id=queue_id,
        )

        if queue.queue_date != today:
            raise HTTPException(
                status_code=400,
                detail="Queue token is not for today",
            )

        if queue.status not in [
            QueueStatusEnum.WAITING,
            QueueStatusEnum.IN_PROGRESS,
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Queue is not active",
            )
            
        if queue.status == QueueStatusEnum.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token number"
            )
            
        if queue.status == QueueStatusEnum.IN_PROGRESS:
            return QueueWaitEstimateResponse(
                token_number=queue.token_number,
                patients_ahead=0,
                estimated_wait_mins=0,
            )

        ahead_query = (
            select(func.count(Queue.id))
            .where(
                Queue.tenant_id == tenant_id,
                Queue.queue_date == today,
                Queue.doctor_id == queue.doctor_id,

                Queue.status.in_([
                    QueueStatusEnum.WAITING,
                    QueueStatusEnum.IN_PROGRESS,
                ]),

                Queue.token_number < queue.token_number,
            )
        )
        # ahead_query = (
        #     select(
        #         func.coalesce(
        #             func.sum(
        #                 Appointment.duration_minutes
        #             ),
        #             0,
        #         )
        #     )
        #     .join(
        #         Appointment,
        #         Appointment.id == Queue.appointment_id,
        #     )
        #     .where(
        #         Queue.tenant_id == tenant_id,
        #         Queue.queue_date == today,
        #         Queue.doctor_id == queue.doctor_id,

        #         Queue.status.in_([
        #             QueueStatusEnum.WAITING,
        #             QueueStatusEnum.IN_PROGRESS,
        #         ]),

        #         Queue.token_number < queue.token_number,
        #     )
        # )

        ahead_result = await db.execute(
            ahead_query
        )

        patients_ahead = (
            ahead_result.scalar() or 0
        )

        # better default
        avg_duration = (
            queue.appointment.duration_minutes
            or 15
        )

        estimated_wait = (
            patients_ahead * avg_duration
        )

        return QueueWaitEstimateResponse(
            token_number=queue.token_number,
            patients_ahead=patients_ahead,
            estimated_wait_mins=estimated_wait,
        )
    
    @staticmethod
    async def get_public_display_for_tokens(
        db: AsyncSession,
        tenant_id: UUID,
    ) -> PublicQueueDisplayResponse:

        today = datetime.now(UTC).date()

        query = (
            select(Queue)
            .where(
                Queue.tenant_id == tenant_id,
                Queue.queue_date == today,
                Queue.status.in_([
                    QueueStatusEnum.WAITING,
                    QueueStatusEnum.IN_PROGRESS,
                ]),
            )
            .options(
                joinedload(Queue.appointment)
                .joinedload(Appointment.doctor)
            )
            .order_by(
                case(
                    (
                        Queue.status
                        == QueueStatusEnum.IN_PROGRESS,
                        0,
                    ),
                    (
                        Queue.status
                        == QueueStatusEnum.WAITING,
                        1,
                    ),
                    else_=2,
                ),
                Queue.token_number.asc(),
            )
        )

        result = await db.execute(query)
        queues = (
            result.scalars()
            .unique()
            .all()
        )

        now_serving = []
        waiting = []

        for queue in queues:

            item = PublicQueueDisplayItem(
                token_number=queue.token_number,

                doctor_name=(
                    queue.appointment.doctor.username
                    if queue.appointment.doctor
                    else None
                ),

                status=queue.status,
            )

            if queue.status == QueueStatusEnum.IN_PROGRESS:
                now_serving.append(item)

            elif queue.status == QueueStatusEnum.WAITING:
                waiting.append(item)

        return PublicQueueDisplayResponse(
            now_serving=now_serving,
            waiting=waiting[:10],  # avoid giant payloads
        )