from uuid import UUID
from datetime import datetime, UTC

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.appointment import Appointment, AppointmentProcedure
from app.models.procedure import ProcedureCatalog
from app.models.queue import Queue
from app.models.patient import Patient
from app.models.user import User, Role, Membership

from app.schemas.appointment import (
    AppointmentListResponse, 
    AppointmentListItem,
    AppointmentCreate,
    AppointmentDetail,
    AppointmentProcedureResponse,
    AppointmentUpdate
)

from app.utils.enums import (
    AppointmentStatusEnum, RoleEnum, QueueStatusEnum, AppointmentTypeEnum
    )

class AppointmentService:

    @staticmethod
    async def list_appointments(
        db: AsyncSession,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 20,
        date_range: str | None = None,
        appointment_status: AppointmentStatusEnum | None = None,
        doctor_id: UUID | None = None,
    ) -> AppointmentListResponse:
        """List appointments for given tenant"""

        filters = [
            Appointment.tenant_id == tenant_id
        ]

        today = datetime.now(UTC).date()
        if date_range == "today":
            filters.append(
                func.date(Appointment.appointment_date) == today
            )
        elif date_range == "upcoming":
            filters.append(
                Appointment.appointment_date >= datetime.now(UTC)
            )
            
        if appointment_status:
            filters.append(
                Appointment.status == appointment_status
            )
        if doctor_id:
            filters.append(
                Appointment.doctor_id == doctor_id
            )

        total_query = select(func.count(Appointment.id)).where(
            *filters
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
        payload: AppointmentCreate
    ) -> AppointmentListItem:
        """Create appointment with planned procedures"""

        # VALIDATE PATIENT
        patient_query = await db.execute(
            select(Patient).where(
                Patient.id == payload.patient_id,
                Patient.tenant_id == tenant_id,
            )
        )

        patient = patient_query.scalar_one_or_none()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found",
            )

        # VALIDATE DOCTOR
        if payload.doctor_id:
            doctor_query = await db.execute(
                select(User)
                .join(Membership, Membership.user_id == User.id)
                .join(Role, Role.id == Membership.role_id)
                .options(selectinload(User.memberships))
                .where(
                    User.id == payload.doctor_id,
                    User.is_active == True,

                    Membership.tenant_id == tenant_id,
                    Membership.is_active.is_(True),
                    
                    Role.name == RoleEnum.DOCTOR.value
                )
            )

            doctor = doctor_query.scalar_one_or_none()
            if not doctor:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Doctor not found",
                )

        # VALIDATE PROCEDURE CATALOGS
        procedure_catalog_ids = [
            procedure.procedure_catalog_id
            for procedure in payload.procedures
        ]

        if procedure_catalog_ids:
            catalog_query = await db.execute(
                select(ProcedureCatalog.id).where(
                    ProcedureCatalog.id.in_(
                        procedure_catalog_ids
                    ),
                    ProcedureCatalog.is_active == True,
                )
            )

            valid_catalog_ids = set(
                catalog_query.scalars().all()
            )

            invalid_catalog_ids = (
                set(procedure_catalog_ids)
                - valid_catalog_ids
            )
            if invalid_catalog_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Invalid procedures selected",
                    ),
                )

        # CREATE APPOINTMENT
        appointment = Appointment(
            tenant_id=tenant_id,

            patient_id=payload.patient_id,
            assigned_doctor_id=payload.doctor_id,

            appointment_type=payload.appointment_type,

            appointment_date=payload.appointment_date,
            duration_minutes=payload.duration_minutes,

            chief_complaint=payload.chief_complaint,
            notes=payload.notes,

            source=payload.source,

            status=AppointmentStatusEnum.BOOKED,
            created_by_id=user_id,
        )

        db.add(appointment)
        await db.flush()

        # CREATE PLANNED PROCEDURES
        planned_procedures = []

        for item in payload.procedures:

            planned = AppointmentProcedure(
                tenant_id=tenant_id,

                appointment_id=appointment.id,
                patient_id=payload.patient_id,

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

            planned_procedures.append(planned)

        db.add_all(planned_procedures)

        # OPTIONAL AUTO QUEUE ENTRY
        # today = datetime.now(UTC).date()
        # appointment_day = (
        #     payload.appointment_date.date()
        # )
        # appointment_type = appointment.appointment_type

        # # only today's appointments enter queue
        # if appointment_day == today and appointment_type == AppointmentTypeEnum.WALK_IN:
        #     token_result = await db.execute(
        #         select(Queue.token_number)
        #         .where(
        #             Queue.tenant_id == tenant_id,
        #             Queue.queue_date == today,
        #         )
        #         .order_by(
        #             Queue.token_number.desc()
        #         )
        #         .limit(1)
        #     )

        #     last_token = token_result.scalar()

        #     next_token = (
        #         (last_token or 0) + 1
        #     )

        #     queue_entry = Queue(
        #         tenant_id=tenant_id,
        #         appointment_id=appointment.id,
        #         queue_date=today,
        #         token_number=next_token,
        #         status=QueueStatusEnum.WAITING,
        #     )

        #     db.add(queue_entry)

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
        return AppointmentListItem.model_validate(
            appointment
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
        
        query = (
            select(Appointment)
            .where(
                Appointment.id == appointment_id,
                Appointment.tenant_id == tenant_id,
            )
            .options(
                selectinload(
                    Appointment.planned_procedures
                )
            )
        )

        result = await db.execute(query)
        appointment = result.scalar_one_or_none()

        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found",
            )

        # VALIDATE DOCTOR
        if payload.doctor_id:
            doctor_exists = await db.scalar(
                select(User)
                .join(Membership, Membership.user_id == User.id)
                .join(Role, Role.id == Membership.role_id)
                .options(selectinload(User.memberships))
                .where(
                    User.id == payload.doctor_id,
                    User.is_active == True,

                    Membership.tenant_id == tenant_id,
                    Membership.is_active.is_(True),
                    
                    Role.name == RoleEnum.DOCTOR
                )
            )

            if not doctor_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Doctor not found",
                )

        # VALIDATE PROCEDURE CATALOGS
        if payload.procedures is not None:
            procedure_catalog_ids = [
                p.procedure_catalog_id
                for p in payload.procedures
            ]

            if procedure_catalog_ids:
                catalog_query = await db.execute(
                    select(ProcedureCatalog.id).where(
                        ProcedureCatalog.id.in_(
                            procedure_catalog_ids
                        ),
                        ProcedureCatalog.is_active.is_(True),
                    )
                )

                valid_catalog_ids = set(
                    catalog_query.scalars().all()
                )

                invalid_catalog_ids = (
                    set(procedure_catalog_ids)
                    - valid_catalog_ids
                )
                if invalid_catalog_ids:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "Invalid procedures selected",
                        ),
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
        appointment.updated_at = datetime.now(UTC)

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
        