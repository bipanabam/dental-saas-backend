from uuid import UUID
from datetime import datetime, UTC

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.patient import Patient, PatientFamilyLink
from app.models.medical_record import MedicalRecord

from app.models.user import Membership, User, Role
from app.models.appointment import Appointment

from app.schemas.patient import (
    PatientListItem, 
    PatientListResponse,
    PatientFilter,
    PatientResponse, 
    PatientDetail, 
    FamilyLinkCreate, 
    FamilyListItem, 
    MedicalRecordSummary, 
    MedicalRecordPayload,
    PatientAppointmentMini,
    PatientSummaryResponse
)
from app.schemas.appointment import AppointmentListResponse, AppointmentFilter

from app.utils.patient_code import generate_patient_code
from app.utils.enums import (
    RoleEnum,
    FamilyRelationshipEnum, 
    PatientStatusEnum, 
)
from app.utils.reverse_relationship import get_reverse_relationship

from app.api.v1.appointments.services import AppointmentService


class PatientService:
    
    @staticmethod
    async def _get_patient_or_404(
        db: AsyncSession,
        tenant_id: UUID,
        patient_id: UUID,
    ) -> Patient:  
        query = (
            select(Patient)
            .join(MedicalRecord)
            .where(
                Patient.tenant_id == tenant_id,
                Patient.id == patient_id
            )
            .options(
                selectinload(Patient.medical_record)
            )
        )
        result = await db.execute(query)
        patient = result.scalar_one_or_none()
        
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
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
    async def create_patient(
        db: AsyncSession,
        user_id: UUID,
        tenant_id: UUID,
        tenant_name: str,
        payload: dict,
    ) -> PatientResponse:
        """Create a new patient for the tenant"""
        # check duplicate
        existing_patient = await db.execute(
            select(Patient).where(
                (Patient.phone == payload.phone) | 
                (Patient.email == payload.email)
            )
        )
        if existing_patient.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Patient with this phone or email already exists"
            )
        
        # generate patient code
        patient_count_result = await db.execute(
            select(Patient).where(Patient.tenant_id == tenant_id)
        )
        patient_count = len(patient_count_result.scalars().all()) + 1
        patient_code = generate_patient_code(patient_id=patient_count, tenant_name=tenant_name)
        
        # create patient
        new_patient = Patient(
            tenant_id=tenant_id,
            patient_code=patient_code,
            first_name=payload.first_name,
            last_name=payload.last_name,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            blood_group=payload.blood_group if payload.blood_group else None,
            phone=payload.phone,
            email=payload.email if payload.email else None,
            address=payload.address if payload.address else None,
            category=payload.category if payload.category else None,
            created_by_id=user_id,
        )
        db.add(new_patient)
        await db.flush()
        # create medical record automatically
        medical_record = MedicalRecord(
            patient_id=new_patient.id,
            allergies=payload.allergies if payload.allergies else None,
            created_by_id=user_id,
        )
        db.add(medical_record)
        
        # Commit Transaction
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create patient due to integrity error."
            )
        await db.refresh(new_patient)
        await db.refresh(medical_record)
        return PatientResponse.model_validate(
            new_patient
        )
    
    @staticmethod    
    async def list_patients(
        db: AsyncSession,
        tenant_id: UUID,
        filter: PatientFilter,
        skip: int = 0,
        limit: int = 20,
    ) -> PatientListResponse:
        """List patients for the tenant with pagination"""
        filters = [
            Patient.tenant_id == tenant_id,
            Patient.status != PatientStatusEnum.INACTIVE
        ]

        if filter.category:
            filters.append(Patient.category == filter.category)

        if filter.status:
            filters.append(Patient.status == filter.status)

        if filter.gender:
            filters.append(Patient.gender == filter.gender)

        if filter.blood_group:
            filters.append(Patient.blood_group == filter.blood_group)
            
        total_query = (
            select(func.count(Patient.id))
            .where(*filters)
        )

        total_result = await db.execute(total_query)
        total = total_result.scalar() or 0

        query = (
            select(Patient)
            .join(MedicalRecord)
            .where(*filters)
            .options(
                selectinload(Patient.medical_record)
            )
            .order_by(Patient.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        patients = result.scalars().unique().all()
        
        if not patients:
            return []
        return PatientListResponse(
            items=[
                PatientListItem.model_validate(
                    patient
                )
                for patient in patients
            ],
            total=total,
            skip=skip,
            limit=limit,
        )
        
    @staticmethod
    async def get_patient_by_id(
        db: AsyncSession,
        tenant_id: UUID,
        patient_id: UUID
    ) -> PatientDetail:
        """Get a specific patient by ID"""
        patient = await PatientService._get_patient_or_404(
            db=db,
            tenant_id=tenant_id,
            patient_id=patient_id
        )
        
        return PatientDetail.model_validate(
            patient
        )
    
    @staticmethod
    async def search_patients(
        db: AsyncSession,
        tenant_id: UUID,
        query: str
    ) -> list[PatientListItem]:
        """Search patients by name, code, phone, or email"""
        search_query = f"%{query}%"
        result = await db.execute(
            select(Patient)
            .where(
                Patient.tenant_id == tenant_id,
                (
                    (Patient.first_name.ilike(search_query)) |
                    (Patient.last_name.ilike(search_query)) |
                    (Patient.patient_code.ilike(search_query)) |
                    (Patient.phone.ilike(search_query)) |
                    (Patient.email.ilike(search_query))
                )
            )
            .order_by(Patient.created_at.desc())
        )
        patients = result.scalars().all()
        
        if not patients:
            return []
        
        return [
            PatientListItem.model_validate(
                patient
            ) for patient in patients
        ]
        
    @staticmethod
    async def check_duplicate_patient(
        db: AsyncSession,
        tenant_id: UUID,
        phone: str | None = None,
        email: str | None = None
    ) -> bool:
        """Check if a patient with the same phone or email already exists"""
        if not phone and not email:
            return False

        query = select(Patient).where(Patient.tenant_id == tenant_id)
        if phone and email:
            query = query.where(
                (Patient.phone == phone) | 
                (Patient.email == email)
            )
        elif phone:
            query = query.where(Patient.phone == phone)
        elif email:
            query = query.where(Patient.email == email)

        result = await db.execute(query)
        existing_patient = result.scalars().first()
        
        if existing_patient:
            return True

        return False
        
    @staticmethod
    async def update_patient(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        patient_id: UUID,
        payload: dict,
    ) -> PatientResponse:
        """Update patient details"""
        patient = await PatientService._get_patient_or_404(
            db=db,
            tenant_id=tenant_id,
            patient_id=patient_id
        )
        
        # Update patient fields
        for field, value in payload.items():
            if hasattr(patient, field) and value is not None:
                setattr(patient, field, value)
        patient.updated_by_id = user_id
        
        # Update medical record fields if present in payload
        # if patient.medical_record:
        #     medical_record = patient.medical_record
        #     for field in ['allergies', 'systemic_conditions', 'current_medications', 'prior_surgeries', 'emergency_contact_name', 'emergency_contact_phone']:
        #         if field in payload and payload[field] is not None:
        #             setattr(medical_record, field, payload[field])
        
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update patient due to integrity error."
            )
        await db.refresh(patient)
        return PatientResponse.model_validate(
            patient
        )
        
    @staticmethod
    async def delete_patient(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        patient_id: UUID
    ):
        """Soft delete a patient by setting status to INACTIVE"""
        patient = await PatientService._get_patient_or_404(
            db=db,
            tenant_id=tenant_id,
            patient_id=patient_id
        )
        
        if patient.status == PatientStatusEnum.INACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Patient is already inactive."
            ) 
        
        patient.status = PatientStatusEnum.INACTIVE
        patient.updated_by_id = user_id
        
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete patient due to integrity error."
            )
            
    @staticmethod
    async def restore_patient(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        patient_id: UUID
    ):
        """Restore soft deleted patient"""
        patient = await PatientService._get_patient_or_404(
            db=db,
            tenant_id=tenant_id,
            patient_id=patient_id
        )
        
        if patient.status == PatientStatusEnum.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Patient is already restored."
            ) 
        
        patient.status = PatientStatusEnum.ACTIVE
        patient.updated_by_id = user_id
        
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to restore patient due to integrity error."
            )
            
    @staticmethod
    async def get_medical_record_summary(
        db: AsyncSession,
        tenant_id: UUID,
        patient_id: UUID
    ) -> MedicalRecordSummary:
        """Get medical record summary for a patient"""
        query = (
            select(MedicalRecord)
            .join(Patient)
            .where(
                MedicalRecord.patient_id == patient_id,
                Patient.tenant_id == tenant_id
            )
        )
        result = await db.execute(query)
        medical_record = result.scalars().first()
        
        if not medical_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medical record not found for this patient"
            )
        
        return MedicalRecordSummary.model_validate(
            medical_record
        )
        
    @staticmethod
    async def create_or_update_medical_record(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        patient_id: UUID,
        payload: MedicalRecordPayload
    ) -> MedicalRecordSummary:
        """Create or update medical record for a patient"""
        query = (
            select(MedicalRecord)
            .join(Patient)
            .where(
                MedicalRecord.patient_id == patient_id,
                Patient.tenant_id == tenant_id
            )
        )
        result = await db.execute(query)
        medical_record = result.scalars().first()
        
        if medical_record:
            # Update existing medical record
            for field in ['allergies', 'systemic_conditions', 'current_medications', 'prior_surgeries', 'emergency_contact_name', 'emergency_contact_phone']:
                if hasattr(payload, field) and getattr(payload, field) is not None:
                    setattr(medical_record, field, getattr(payload, field))
            medical_record.updated_by_id = user_id
        else:
            # Create new medical record
            medical_record = MedicalRecord(
                patient_id=patient_id,
                allergies=payload.allergies if payload.allergies else None,
                systemic_conditions=payload.systemic_conditions if payload.systemic_conditions else None,
                current_medications=payload.current_medications if payload.current_medications else None,
                prior_surgeries=payload.prior_surgeries if payload.prior_surgeries else None,
                emergency_contact_name=payload.emergency_contact_name if payload.emergency_contact_name else None,
                emergency_contact_phone=payload.emergency_contact_phone if payload.emergency_contact_phone else None, 
                created_by_id=user_id,
            )
            db.add(medical_record)
        
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create/update medical record due to integrity error."
            )
        
        await db.refresh(medical_record)
        
        return MedicalRecordSummary.model_validate(
            medical_record
        )
    
    @staticmethod
    async def assign_primary_doctor(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        patient_id: UUID,
        doctor_id: UUID
    ) -> MedicalRecordSummary:
        """Assign or change primary doctor for a patient"""
        query = (
            select(MedicalRecord)
            .join(Patient)
            .where(
                MedicalRecord.patient_id == patient_id,
                Patient.tenant_id == tenant_id
            )
        )
        result = await db.execute(query)
        medical_record = result.scalars().first()
        
        if not medical_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medical record not found for this patient"
            )
            
        # verify doctor exists and is active
        await PatientService._validate_doctor(
            db=db,
            tenant_id=tenant_id,
            doctor_id=doctor_id
        )

        medical_record.primary_doctor_id = doctor_id
        medical_record.updated_by_id = user_id
        
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to assign primary doctor due to integrity error."
            )
        
        await db.refresh(medical_record)
        
        return MedicalRecordSummary.model_validate(
            medical_record
        )  
        
    @staticmethod
    async def list_family_members(
        db: AsyncSession,
        tenant_id: UUID,
        primary_account_id: UUID
    ) -> list[FamilyListItem]:
        """List family members for a given patient"""

        query = (
            select(PatientFamilyLink)
            .where(
                PatientFamilyLink.tenant_id == tenant_id,
                PatientFamilyLink.primary_patient_id == primary_account_id
            )
            .options(
                selectinload(PatientFamilyLink.family_member)
            )
            .order_by(PatientFamilyLink.created_at.desc())
        )

        result = await db.execute(query)
        family_links = result.scalars().all()

        if not family_links:
            return []

        return [
            FamilyListItem(
                id=link.family_member.id,
                first_name=link.family_member.first_name,
                last_name=link.family_member.last_name,
                relationship_type=(
                    link.relationship_type.value
                    if link.relationship_type
                    else None
                )
            )
            for link in family_links
        ]
        
    @staticmethod
    async def add_family_member(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        primary_account_id: UUID,
        payload: FamilyLinkCreate
    ) -> FamilyListItem:
        """Link an existing patient as family member"""
        
        # prevent self-linking
        if primary_account_id == payload.family_member_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Patient cannot be linked to themselves"
            )

        # verify primary patient exists
        primary_patient_result = await db.execute(
            select(Patient).where(
                Patient.tenant_id == tenant_id,
                Patient.id == primary_account_id
            )
        )

        primary_patient = primary_patient_result.scalars().first()
        if not primary_patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Primary patient not found"
            )

        # verify family member exists
        family_member_result = await db.execute(
            select(Patient).where(
                Patient.tenant_id == tenant_id,
                Patient.id == payload.family_member_id
            )
        )

        family_member = family_member_result.scalars().first()
        if not family_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Family member not found"
            )

        # prevent duplicate link
        existing_link_result = await db.execute(
            select(PatientFamilyLink).where(
                PatientFamilyLink.tenant_id == tenant_id,
                PatientFamilyLink.primary_patient_id == primary_account_id,
                PatientFamilyLink.family_member_id == payload.family_member_id
            )
        )

        existing_link = existing_link_result.scalars().first()

        if existing_link:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Family member already linked"
            )

        # create link
        relationship_type  = payload.relationship_type if payload.relationship_type else FamilyRelationshipEnum.OTHER
        reverse_relationship = get_reverse_relationship(
            relationship=relationship_type,
            patient_gender=primary_patient.gender
        )
        forward_link = PatientFamilyLink(
            tenant_id=tenant_id,
            primary_patient_id=primary_account_id,
            family_member_id=payload.family_member_id,
            relationship_type=relationship_type,
            created_by_id=user_id,
            updated_by_id=user_id,
        )
        reverse_link = PatientFamilyLink(
            tenant_id=tenant_id,
            primary_patient_id=payload.family_member_id,
            family_member_id=primary_account_id,
            relationship_type=reverse_relationship,
            created_by_id=user_id,
            updated_by_id=user_id,
        )

        db.add_all([
            forward_link,
            reverse_link
        ])

        try:
            await db.commit()
            await db.refresh(forward_link)
        except Exception as e:
            await db.rollback()
            raise e

        return FamilyListItem(
            id=family_member.id,
            first_name=family_member.first_name,
            last_name=family_member.last_name,
            relationship_type=(
                forward_link.relationship_type
                if forward_link.relationship_type
                else None
            )
        )
        
    @staticmethod
    async def remove_family_member(
        db: AsyncSession,
        tenant_id: UUID,
        primary_account_id: UUID,
        family_member_id: UUID
    ):
        """Unlink a family member from the patient"""

        # verify link exists
        link_result = await db.execute(
            select(PatientFamilyLink).where(
                PatientFamilyLink.tenant_id == tenant_id,
                PatientFamilyLink.primary_patient_id == primary_account_id,
                PatientFamilyLink.family_member_id == family_member_id
            )
        )

        link = link_result.scalars().first()

        if not link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Family link not found"
            )

        # delete both forward and reverse links
        reverse_link_result = await db.execute(
            select(PatientFamilyLink).where(
                PatientFamilyLink.tenant_id == tenant_id,
                PatientFamilyLink.primary_patient_id == family_member_id,
                PatientFamilyLink.family_member_id == primary_account_id
            )
        )

        reverse_link = reverse_link_result.scalars().first()
        if not reverse_link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reverse family link not found"
            )

        await db.delete(link)
        await db.delete(reverse_link)

        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise e
        
    @staticmethod
    async def get_appointments(
        db: AsyncSession,
        tenant_id: UUID,
        patient_id: UUID,
        filter: AppointmentFilter,
        skip: int = 0,
        limit: int = 20,
    ) -> AppointmentListResponse:
        """
        List all appointments for a patient.
        """

        # ENSURE PATIENT EXISTS
        await PatientService._get_patient_or_404(
            db=db,
            tenant_id=tenant_id,
            patient_id=patient_id
        )
        
        return await AppointmentService.list_patient_appointments(
            db=db,
            tenant_id=tenant_id,
            patient_id=patient_id,
            filter=filter,
            skip=skip,
            limit=limit
        )
        
    @staticmethod
    async def get_patient_summary(
        db: AsyncSession,
        tenant_id: UUID,
        patient_id: UUID,
    ) -> PatientSummaryResponse:
        """Get printable patient summary"""

        query = (
            select(Patient)
            .where(
                Patient.id == patient_id,
                Patient.tenant_id == tenant_id,
            )
            .options(
                joinedload(Patient.medical_record)
                .joinedload(MedicalRecord.primary_doctor),

                selectinload(Patient.appointments),
            )
        )

        result = await db.execute(query)
        patient = result.scalar_one_or_none()

        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found",
            )

        now = datetime.now(UTC)

        latest_appointment = None
        upcoming_appointment = None

        appointments = sorted(
            patient.appointments,
            key=lambda a: a.appointment_date,
            reverse=True,
        )

        # latest completed/in-progress/checkedin
        for appointment in appointments:
            if appointment.appointment_date <= now:
                latest_appointment = appointment
                break

        # next upcoming
        future_appointments = sorted(
            [
                a for a in patient.appointments
                if a.appointment_date > now
            ],
            key=lambda a: a.appointment_date,
        )

        if future_appointments:
            upcoming_appointment = (
                future_appointments[0]
            )

        medical_record = patient.medical_record

        primary_doctor_name = None

        if (
            medical_record
            and medical_record.primary_doctor
        ):
            primary_doctor_name = (
                f"{medical_record.primary_doctor.username} "
            )

        return PatientSummaryResponse(
            id=patient.id,
            patient_code=patient.patient_code,

            first_name=patient.first_name,
            last_name=patient.last_name,

            phone=patient.phone,
            email=patient.email,

            gender=patient.gender,
            blood_group=patient.blood_group,
            date_of_birth=patient.date_of_birth,

            status=patient.status,

            visit_count=patient.visit_count,
            last_visit_at=patient.last_visit_at,

            allergies=(
                medical_record.allergies
                if medical_record
                else None
            ),

            systemic_conditions=(
                medical_record.systemic_conditions
                if medical_record
                else None
            ),

            current_medications=(
                medical_record.current_medications
                if medical_record
                else None
            ),

            primary_doctor_name=(
                primary_doctor_name
            ),

            latest_appointment=(
                PatientAppointmentMini.model_validate(
                    latest_appointment
                )
                if latest_appointment
                else None
            ),

            upcoming_appointment=(
                PatientAppointmentMini.model_validate(
                    upcoming_appointment
                )
                if upcoming_appointment
                else None
            ),
        )