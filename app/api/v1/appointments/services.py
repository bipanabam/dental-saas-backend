from uuid import UUID
from datetime import datetime, UTC, date

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.appointment import Appointment, AppointmentProcedure
from app.models.procedure import ProcedureCatalog
from app.models.queue import Queue
from app.models.patient import Patient
from app.models.user import User, Role, Membership

from app.schemas.appointment import (
    AppointmentListResponse, 
    AppointmentFilter,
    AppointmentListItem,
    AppointmentCreate,
    AppointmentProcedureCreate,
    AppointmentCreateWalkIn,
    AppointmentDetail,
    AppointmentProcedureResponse,
    AppointmentUpdate,
    AppointmentCancel,
    AppointmentReschedule,
    AppointmentFollowUpCreate,
    AppointmentCheckInResponse
)

from app.utils.enums import (
    AppointmentStatusEnum, 
    RoleEnum, 
    QueueStatusEnum, 
    AppointmentTypeEnum
    )

class AppointmentService:
    
    @staticmethod
    async def _get_appointment(
        db: AsyncSession,
        tenant_id: UUID,
        appointment_id: UUID,
    ) -> Appointment:
        query = (
            select(Appointment)
            .where(
                Appointment.id == appointment_id,
                Appointment.tenant_id == tenant_id,
            )
            .options(
                joinedload(Appointment.queue_entry),
                selectinload(Appointment.planned_procedures),
            )
        )

        result = await db.execute(query)

        appointment = result.scalar_one_or_none()

        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found",
            )

        return appointment
    
    @staticmethod
    async def _validate_patient(
        db: AsyncSession,
        tenant_id: UUID,
        patient_id: UUID,
    ) -> Patient:
        """
        Ensure patient exists inside tenant.
        """

        result = await db.execute(
            select(Patient).where(
                Patient.id == patient_id,
                Patient.tenant_id == tenant_id,
            )
        )

        patient = result.scalar_one_or_none()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found",
            )

        return patient
    
    @staticmethod
    async def _validate_doctor(
        db: AsyncSession,
        tenant_id: UUID,
        doctor_id: UUID | None,
    ) -> User | None:
        """
        Ensure assigned doctor exists and belongs to tenant.
        """

        if not doctor_id:
            return None

        result = await db.execute(
            select(User)
            .join(
                Membership,
                Membership.user_id == User.id,
            )
            .join(
                Role,
                Role.id == Membership.role_id,
            )
            .options(
                selectinload(User.memberships)
            )
            .where(
                User.id == doctor_id,
                User.is_active.is_(True),

                Membership.tenant_id == tenant_id,
                Membership.is_active.is_(True),

                Role.name == RoleEnum.DOCTOR.value,
            )
        )

        doctor = result.scalar_one_or_none()

        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor not found",
            )

        return doctor
    
    
    @staticmethod
    async def _validate_procedure_catalogs(
        db: AsyncSession,
        procedure_items: list[
            AppointmentProcedureCreate
        ],
    ) -> None:
        """
        Ensure all selected procedure catalogs are valid.
        """

        procedure_catalog_ids = [
            item.procedure_catalog_id
            for item in procedure_items
        ]

        if not procedure_catalog_ids:
            return

        result = await db.execute(
            select(ProcedureCatalog.id).where(
                ProcedureCatalog.id.in_(
                    procedure_catalog_ids
                ),
                ProcedureCatalog.is_active.is_(True),
            )
        )

        valid_catalog_ids = set(
            result.scalars().all()
        )

        invalid_catalog_ids = (
            set(procedure_catalog_ids)
            - valid_catalog_ids
        )

        if invalid_catalog_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Invalid procedures selected"
                ),
            )
            
    @staticmethod
    def _create_planned_procedures(
        tenant_id: UUID,
        appointment_id: UUID,
        patient_id: UUID,
        procedure_items: list[
            AppointmentProcedureCreate
        ],
    ) -> list[AppointmentProcedure]:
        """
        Build planned procedure ORM objects.
        """

        planned_procedures = []

        for item in procedure_items:

            planned = AppointmentProcedure(
                tenant_id=tenant_id,

                appointment_id=appointment_id,
                patient_id=patient_id,

                procedure_catalog_id=(
                    item.procedure_catalog_id
                ),

                tooth_numbers=item.tooth_numbers,

                estimated_cost=(
                    item.estimated_cost
                ),

                estimated_duration_minutes=(
                    item.estimated_duration_minutes
                ),

                notes=item.notes,
            )

            planned_procedures.append(
                planned
            )

        return planned_procedures
    
    @staticmethod
    async def _create_queue_entry(
        db: AsyncSession,
        tenant_id: UUID,
        appointment: Appointment,
    ) -> Queue:
        """
        Create queue entry safely.
        """

        today = datetime.now(UTC).date()
        MAX_RETRIES = 3

        for _ in range(MAX_RETRIES):

            token_result = await db.execute(
                select(func.max(Queue.token_number))
                .where(
                    Queue.tenant_id == tenant_id,
                    Queue.queue_date == today,
                )
            )

            next_token = (token_result.scalar() or 0) + 1
            queue_entry = Queue(
                tenant_id=tenant_id,
                appointment_id=appointment.id,
                doctor_id=appointment.assigned_doctor_id,
                queue_date=today,
                token_number=next_token,
                status=QueueStatusEnum.WAITING,
            )

            db.add(queue_entry)

            try:
                await db.flush()
                return queue_entry

            except IntegrityError:
                await db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Failed generating queue token",
        )

    @staticmethod
    async def list_appointments(
        db: AsyncSession,
        tenant_id: UUID,
        filter: AppointmentFilter,
        skip: int = 0,
        limit: int = 20,
    ) -> AppointmentListResponse:
        """List appointments for given tenant"""

        filters = [
            Appointment.tenant_id == tenant_id
        ]

        # today = datetime.now(UTC).date()
        if filter.date_range:
            filters.append(
                func.date(Appointment.appointment_date) == filter.date_range
            )
        if filter.status:
            filters.append(
                Appointment.status == filter.status
            )
        if filter.doctor_id:
            filters.append(
                Appointment.assigned_doctor_id
                == filter.doctor_id
            )
        if filter.appointment_type:
            filters.append(
                Appointment.appointment_type
                == filter.appointment_type
            )
        if filter.source:
            filters.append(
                Appointment.source
                == filter.source
            )

        total_query = (
            select(func.count(Appointment.id))
            .where(*filters)
        )

        total_result = await db.execute(total_query)
        total = total_result.scalar() or 0
        query = (
            select(Appointment)
            .where(*filters)
            .options(
                selectinload(Appointment.planned_procedures),
                selectinload(Appointment.queue_entry),
            )
            .order_by(Appointment.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(query)
        appointments = result.scalars().unique().all()

        return AppointmentListResponse(
            items=[
                AppointmentListItem.model_validate(
                    appointment
                )
                for appointment in appointments
            ],
            total=total,
            skip=skip,
            limit=limit,
        )
        
    @staticmethod
    async def create_appointment(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        payload: AppointmentCreate,
    ) -> AppointmentListItem:

        # VALIDATIONS
        await AppointmentService._validate_patient(
            db=db,
            tenant_id=tenant_id,
            patient_id=payload.patient_id,
        )

        await AppointmentService._validate_doctor(
            db=db,
            tenant_id=tenant_id,
            doctor_id=payload.doctor_id,
        )

        await (
            AppointmentService
            ._validate_procedure_catalogs(
                db=db,
                procedure_items=payload.procedures,
            )
        )

        # CREATE APPOINTMENT
        appointment = Appointment(
            tenant_id=tenant_id,

            patient_id=payload.patient_id,
            assigned_doctor_id=payload.doctor_id,

            appointment_type=(
                payload.appointment_type
            ),

            appointment_date=(
                payload.appointment_date
            ),

            duration_minutes=(
                payload.duration_minutes
            ),

            chief_complaint=(
                payload.chief_complaint
            ),

            notes=payload.notes,
            source=payload.source,

            status=(
                AppointmentStatusEnum.BOOKED
            ),
            created_by_id=user_id,
        )

        db.add(appointment)
        await db.flush()

        # PROCEDURES
        planned_procedures = (
            AppointmentService
            ._create_planned_procedures(
                tenant_id=tenant_id,
                appointment_id=appointment.id,
                patient_id=payload.patient_id,
                procedure_items=payload.procedures,
            )
        )

        db.add_all(planned_procedures)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=400,
                detail=(
                    "Failed to create appointment"
                ),
            )

        await db.refresh(appointment)
        return AppointmentListItem.model_validate(
            appointment
        )
        
    @staticmethod
    async def walk_in_appointment(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        payload: AppointmentCreateWalkIn
    ) -> AppointmentCheckInResponse:
        """Create a walk in appointment with planned procedures and token by default"""

        # VALIDATIONS
        await AppointmentService._validate_patient(
            db=db,
            tenant_id=tenant_id,
            patient_id=payload.patient_id,
        )

        await AppointmentService._validate_doctor(
            db=db,
            tenant_id=tenant_id,
            doctor_id=payload.doctor_id,
        )

        await (
            AppointmentService
            ._validate_procedure_catalogs(
                db=db,
                procedure_items=payload.procedures,
            )
        )

        # CREATE APPOINTMENT
        appointment = Appointment(
            tenant_id=tenant_id,

            patient_id=payload.patient_id,
            assigned_doctor_id=payload.doctor_id,

            appointment_type=AppointmentTypeEnum.WALK_IN,

            appointment_date=datetime.now(UTC),
            duration_minutes=payload.duration_minutes,

            chief_complaint=payload.chief_complaint,
            notes=payload.notes,

            source=payload.source,

            status=AppointmentStatusEnum.CHECKED_IN,
            created_by_id=user_id,
        )

        db.add(appointment)
        await db.flush()

        # CREATE PLANNED PROCEDURES
        planned_procedures = (
            AppointmentService
            ._create_planned_procedures(
                tenant_id=tenant_id,
                appointment_id=appointment.id,
                patient_id=payload.patient_id,
                procedure_items=payload.procedures,
            )
        )
        db.add_all(planned_procedures)
        
        # ADD QUEUE
        queue_entry = await AppointmentService._create_queue_entry(
            db=db,
            tenant_id=tenant_id,
            appointment=appointment
        )

        # COMMIT
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create appointment",
            )

        await db.refresh(appointment)
        return AppointmentCheckInResponse(
            token_number=queue_entry.token_number,
            queue_id=queue_entry.id,
            queue_status=queue_entry.status,
            appointment=AppointmentListItem.model_validate(
                appointment
            ),
        )
        
    @staticmethod
    async def get_appointment_detail(
        db: AsyncSession,
        tenant_id: UUID,
        appointment_id: UUID,
    ) -> AppointmentDetail:
        """Get single appointment detail"""

        query = (
            select(Appointment)
            .where(
                Appointment.id == appointment_id,
                Appointment.tenant_id == tenant_id,
            )
            .options(
                selectinload(
                    Appointment.planned_procedures
                ).selectinload(
                    AppointmentProcedure.procedure_catalog
                ),
                joinedload(Appointment.queue_entry),
            )
        )

        result = await db.execute(query)
        appointment = result.scalar_one_or_none()

        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found",
            )

        created_by_name = None

        if appointment.created_by_id:
            created_by_query = (
                select(User.username)
                .where(
                    User.id == appointment.created_by_id
                )
            )
            created_by_result = await db.execute(
                created_by_query
            )
            created_by_name = (
                created_by_result.scalar_one_or_none()
            )

        return AppointmentDetail(
            id=appointment.id,
            patient_id=appointment.patient_id,
            assigned_doctor_id=appointment.assigned_doctor_id,

            appointment_type=appointment.appointment_type,
            appointment_date=appointment.appointment_date,
            duration_minutes=appointment.duration_minutes,

            chief_complaint=appointment.chief_complaint,
            notes=appointment.notes,

            source=appointment.source,
            status=appointment.status,
            payment_status=appointment.payment_status,
            cancellation_reason=appointment.cancellation_reason,

            procedures=[
                AppointmentProcedureResponse.model_validate(
                    procedure
                )
                for procedure in appointment.planned_procedures
            ],

            created_at=appointment.created_at,
            updated_at=appointment.updated_at,

            created_by=created_by_name,
        )
        
    @staticmethod
    async def update_appointment(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        appointment_id: UUID,
        payload: AppointmentUpdate
    ) -> AppointmentListItem:
        """Update appointment with planned procedures"""
        
        appointment = await AppointmentService._get_appointment(
            db=db,
            tenant_id=tenant_id,
            appointment_id=appointment_id,
        )
        
        # VALIDATE DOCTOR
        await AppointmentService._validate_doctor(
            db=db,
            tenant_id=tenant_id,
            doctor_id=payload.doctor_id,
        )

        # VALIDATE PROCEDURE CATALOGS
        await (
            AppointmentService
            ._validate_procedure_catalogs(
                db=db,
                procedure_items=payload.procedures,
            )
        )

        # UPDATE APPOINTMENT
        update_data = payload.model_dump(
            exclude_unset=True,
            exclude={"procedures"},
        )
        for field, value in update_data.items():
            if hasattr(appointment, field) and value is not None:
                setattr(appointment, field, value)
        appointment.updated_by_id = user_id

        # REPLACE PLANNED PROCEDURES
        if payload.procedures is not None:
            appointment.planned_procedures.clear()
            
            for item in payload.procedures:
                appointment.planned_procedures.append(
                    AppointmentProcedure(
                        tenant_id=tenant_id,
                        patient_id=appointment.patient_id,

                        procedure_catalog_id=(
                            item.procedure_catalog_id
                        ),
                        tooth_numbers=item.tooth_numbers,
                        estimated_cost=(
                            item.estimated_cost
                        ),
                        estimated_duration_minutes=(
                            item.estimated_duration_minutes
                        ),
                        notes=item.notes,
                    )
                )

        # COMMIT
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update appointment",
            )

        await db.refresh(appointment)
        return AppointmentListItem.model_validate(
            appointment
        )
        
    @staticmethod
    async def cancel_appointment(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        appointment_id: UUID,
        payload: AppointmentCancel
    ) -> None:
        """
        Cancel appointment safely.
        - Remove active queue entry if exists
        - Preserve history/auditability
        """

        appointment = await AppointmentService._get_appointment(
            db=db,
            tenant_id=tenant_id,
            appointment_id=appointment_id,
        )

        # prevent duplicate cancellation
        if (
            appointment.status
            == AppointmentStatusEnum.CANCELLED
        ):
            return

        # Prevent cancellation after completion
        if (
            appointment.status
            == AppointmentStatusEnum.COMPLETED
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Completed appointments "
                    "cannot be cancelled"
                ),
            )

        # CANCEL APPOINTMENT
        appointment.status = (
            AppointmentStatusEnum.CANCELLED
        )
        appointment.cancellation_reason_type = (
            payload.cancellation_reason_type
        )
        appointment.cancellation_reason_note = (
            payload.cancellation_reason_note
        )
        appointment.updated_by_id = user_id
        appointment.updated_at = datetime.now(UTC)

        # HANDLE QUEUE ENTRY
        if appointment.queue_entry:
            queue_entry = appointment.queue_entry

            if queue_entry.status not in [
                QueueStatusEnum.COMPLETED,
            ]:
                queue_entry.status = (
                    QueueStatusEnum.CANCELLED
                )
                queue_entry.cancelled_at = datetime.now(UTC)

        try:
            await db.commit()
        except SQLAlchemyError as e:
            await db.rollback()
            print(e)

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel appointment",
            )
     
     

# AppointmentWorkflowService 
class AppointmentWorkflowService:
    @staticmethod
    async def _get_appointment_or_404(
        db: AsyncSession,
        tenant_id: UUID,
        appointment_id: UUID,
    ) -> Appointment:  
        query = (
            select(Appointment)
            .where(
                Appointment.id == appointment_id,
                Appointment.tenant_id == tenant_id,
            )
            .options(
                joinedload(Appointment.queue_entry),
                joinedload(Appointment.patient),
                selectinload(Appointment.planned_procedures),
            )
        )

        result = await db.execute(query)

        appointment = result.scalar_one_or_none()

        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found",
            )

        return appointment
    
    @staticmethod
    def _ensure_not_cancelled(
        appointment: Appointment,
    ) -> None:
        if (
            appointment.status
            == AppointmentStatusEnum.CANCELLED
        ):
            raise HTTPException(
                status_code=400,
                detail="Appointment is already cancelled",
            )


    @staticmethod
    def _ensure_not_completed(
        appointment: Appointment,
    ) -> None:
        if (
            appointment.status
            == AppointmentStatusEnum.COMPLETED
        ):
            raise HTTPException(
                status_code=400,
                detail="Appointment already completed",
            )
    
    @staticmethod
    async def _create_queue_entry(
        db: AsyncSession,
        tenant_id: UUID,
        appointment: Appointment,
    ) -> Queue:
        """
        Create queue entry safely.
        """

        if appointment.queue_entry:
            return appointment.queue_entry

        today = datetime.now(UTC).date()
        MAX_RETRIES = 3

        for _ in range(MAX_RETRIES):

            token_result = await db.execute(
                select(func.max(Queue.token_number))
                .where(
                    Queue.tenant_id == tenant_id,
                    Queue.queue_date == today,
                )
            )

            next_token = (token_result.scalar() or 0) + 1
            queue_entry = Queue(
                tenant_id=tenant_id,
                appointment_id=appointment.id,
                doctor_id=appointment.assigned_doctor_id,
                queue_date=today,
                token_number=next_token,
                status=QueueStatusEnum.WAITING,
            )

            db.add(queue_entry)

            try:
                await db.flush()
                return queue_entry

            except IntegrityError:
                await db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Failed generating queue token",
        )

    
    @staticmethod
    async def _cancel_queue_entry():
        pass
    
    @staticmethod
    async def _convert_planned_to_actual_procedures():
        pass
    
    @staticmethod
    async def confirm_appointment(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        appointment_id: UUID,
    ) -> AppointmentListItem:

        appointment = await AppointmentWorkflowService._get_appointment_or_404(
            db=db,
            tenant_id=tenant_id,
            appointment_id=appointment_id,
        )

        if appointment.status != AppointmentStatusEnum.BOOKED:
            raise HTTPException(
                status_code=400,
                detail="Only booked appointments can be confirmed",
            )

        appointment.status = AppointmentStatusEnum.CONFIRMED
        appointment.updated_by_id = user_id

        await db.commit()
        await db.refresh(appointment)

        return AppointmentListItem.model_validate(
            appointment
        )
        
    @staticmethod
    async def check_in_appointment(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        appointment_id: UUID,
    ) -> AppointmentCheckInResponse:

        appointment = await (
            AppointmentWorkflowService
            ._get_appointment_or_404(
                db=db,
                tenant_id=tenant_id,
                appointment_id=appointment_id,
            )
        )

        AppointmentWorkflowService._ensure_not_cancelled(
            appointment
        )
        AppointmentWorkflowService._ensure_not_completed(
            appointment
        )

        if appointment.status not in [
            AppointmentStatusEnum.BOOKED,
            AppointmentStatusEnum.CONFIRMED,
        ]:
            raise HTTPException(
                status_code=400,
                detail="Appointment cannot be checked in",
            )
            
        today = datetime.now(UTC).date()
        appointment_day = (
            appointment.appointment_date.date()
        )

        if appointment_day != today:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Only today's appointments "
                    "can be checked in"
                ),
            )

        appointment.status = (
            AppointmentStatusEnum.CHECKED_IN
        )
        appointment.updated_by_id = user_id

        queue_entry = await AppointmentWorkflowService._create_queue_entry(
            db=db,
            tenant_id=tenant_id,
            appointment=appointment,
        )

        try:
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()

            raise HTTPException(
                status_code=500,
                detail="Failed to check in appointment",
            )

        await db.refresh(appointment)
        return AppointmentCheckInResponse(
            token_number=queue_entry.token_number,
            queue_id=queue_entry.id,
            queue_status=queue_entry.status,
            appointment=AppointmentListItem.model_validate(
                appointment
            ),
        )
        
    @staticmethod
    async def start_appointment(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        appointment_id: UUID,
    ) -> AppointmentListItem:
        """
        -CHECKED_IN → IN_PROGRESS
        -queue.started_at
        -queue.status = IN_PROGRESS
        -convert planned to actual_procedures(optional)
        """
        appointment = await (
            AppointmentWorkflowService
            ._get_appointment_or_404(
                db=db,
                tenant_id=tenant_id,
                appointment_id=appointment_id,
            )
        )

        if (
            appointment.status
            != AppointmentStatusEnum.CHECKED_IN
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Only checked-in appointments "
                    "can be started"
                ),
            )

        appointment.status = (
            AppointmentStatusEnum.IN_PROGRESS
        )
        appointment.updated_by_id = user_id

        if appointment.queue_entry:
            appointment.queue_entry.status = (
                QueueStatusEnum.IN_PROGRESS
            )

            appointment.queue_entry.started_at = (
                datetime.now(UTC)
            )

        try:
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()

            raise HTTPException(
                status_code=500,
                detail="Failed to start appointment",
            )

        await db.refresh(appointment)

        return AppointmentListItem.model_validate(
            appointment
        )
        
    @staticmethod
    async def complete_appointment(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        appointment_id: UUID,
    ) -> AppointmentListItem:

        appointment = await (
            AppointmentWorkflowService
            ._get_appointment_or_404(
                db=db,
                tenant_id=tenant_id,
                appointment_id=appointment_id,
            )
        )

        if (
            appointment.status
            != AppointmentStatusEnum.IN_PROGRESS
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Appointment must be in progress"
                ),
            )

        appointment.status = (
            AppointmentStatusEnum.COMPLETED
        )
        appointment.updated_by_id = user_id

        # UPDATE PATIENT STATS
        appointment.patient.visit_count += 1
        appointment.patient.last_visit_at = (
            datetime.now(UTC)
        )

        # COMPLETE QUEUE
        if appointment.queue_entry:
            appointment.queue_entry.status = (
                QueueStatusEnum.COMPLETED
            )

            appointment.queue_entry.completed_at = (
                datetime.now(UTC)
            )

        try:
            await db.commit()
        except SQLAlchemyError as e:
            await db.rollback()
            print(e)

            raise HTTPException(
                status_code=500,
                detail="Failed to complete appointment",
            )

        await db.refresh(appointment)

        return AppointmentListItem.model_validate(
            appointment
        )
        
    @staticmethod
    async def mark_no_show(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        appointment_id: UUID,
    ) -> AppointmentListItem:

        appointment = await (
            AppointmentWorkflowService
            ._get_appointment_or_404(
                db=db,
                tenant_id=tenant_id,
                appointment_id=appointment_id,
            )
        )

        AppointmentWorkflowService._ensure_not_completed(
            appointment
        )

        appointment.status = (
            AppointmentStatusEnum.NO_SHOW
        )

        appointment.updated_by_id = user_id

        if appointment.queue_entry:
            appointment.queue_entry.status = (
                QueueStatusEnum.NO_SHOW
            )

        try:
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()

            raise HTTPException(
                status_code=500,
                detail="Failed to mark no-show",
            )

        await db.refresh(appointment)

        return AppointmentListItem.model_validate(
            appointment
        )
        
    @staticmethod
    async def reschedule_appointment(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        appointment_id: UUID,
        payload: AppointmentReschedule,
    ) -> AppointmentListItem:

        appointment = await AppointmentWorkflowService._get_appointment_or_404(
            db=db,
            tenant_id=tenant_id,
            appointment_id=appointment_id,
        )
        
        AppointmentWorkflowService._ensure_not_completed(
            appointment
        ) 

        appointment.appointment_date = (
            payload.appointment_date
        )

        if payload.assigned_doctor_id:
            appointment.assigned_doctor_id = (
                payload.assigned_doctor_id
            )

        if payload.notes:
            appointment.notes = payload.notes

        appointment.status = AppointmentStatusEnum.BOOKED
        appointment.appointment_type = AppointmentTypeEnum.RESCHEDULED
        appointment.updated_by_id = user_id

        await db.commit()
        await db.refresh(appointment)

        return AppointmentListItem.model_validate(
            appointment
        )
        
    @staticmethod
    async def create_follow_up(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        appointment_id: UUID,
        payload: AppointmentFollowUpCreate,
    ) -> AppointmentListItem:

        parent = await AppointmentWorkflowService._get_appointment_or_404(
            db=db,
            tenant_id=tenant_id,
            appointment_id=appointment_id,
        )

        follow_up = Appointment(
            tenant_id=tenant_id,
            patient_id=parent.patient_id,

            assigned_doctor_id=(
                payload.assigned_doctor_id
                or parent.assigned_doctor_id
            ),

            appointment_type=AppointmentTypeEnum.FOLLOW_UP,

            appointment_date=payload.appointment_date,

            chief_complaint=payload.chief_complaint,
            notes=payload.notes,

            follow_up_from_id=parent.id,

            created_by_id=user_id,
        )

        db.add(follow_up)
        
        # copy previous procedures
        planned_procedures = [
            AppointmentProcedure(
                tenant_id=tenant_id,
                patient_id=parent.patient_id,
                procedure_catalog_id=(
                    item.procedure_catalog_id
                ),
                tooth_numbers=item.tooth_numbers,
                estimated_cost=item.estimated_cost,
                estimated_duration_minutes=(
                    item.estimated_duration_minutes
                ),
                notes=item.notes,
            )
            for item in parent.planned_procedures
        ]
        follow_up.planned_procedures.extend(
            planned_procedures
        )
        
        try:
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()

            raise HTTPException(
                status_code=500,
                detail="Failed to create follow-up appointment",
            )
            
        await db.refresh(follow_up)

        return AppointmentListItem.model_validate(
            follow_up
        )
     