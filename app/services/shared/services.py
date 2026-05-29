from uuid import UUID
from datetime import datetime, UTC

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.appointment import Appointment, AppointmentProcedure
from app.models.procedure import ProcedureCatalog
from app.models.queue import Queue
from app.models.patient import Patient
from app.models.user import User, Role, Membership

from app.schemas.appointment import (
    AppointmentProcedureCreate,
)

from app.utils.enums import (
    RoleEnum, 
    QueueStatusEnum, 
    )

class SharedService:
    
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

        today = datetime.now(UTC).date()

        for _ in range(3):

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
                called_at=datetime.now(UTC),
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