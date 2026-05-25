from uuid import UUID
from datetime import datetime, UTC

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.patient import Patient
from app.models.medical_record import MedicalRecord

from app.schemas.patient import MedicalRecordSummary, PatientResponse, PatientListItem, PatientDetail

from app.utils.patient_code import generate_patient_code
from app.utils.enums import PatientCategoryEnum, PatientStatusEnum, GenderEnum, BloodGroupEnum


class PatientService:

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
            updated_by_id=user_id,
        )
        db.add(new_patient)
        await db.flush()
        # create medical record automatically
        medical_record = MedicalRecord(
            patient_id=new_patient.id,
            allergies=payload.allergies if payload.allergies else None
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
        return PatientResponse(
            id=new_patient.id,
            patient_code=new_patient.patient_code,
            first_name=new_patient.first_name,
            last_name=new_patient.last_name,
            date_of_birth=new_patient.date_of_birth,
            gender=new_patient.gender,
            blood_group=new_patient.blood_group,
            phone=new_patient.phone,
            email=new_patient.email,
            address=new_patient.address,
            category=new_patient.category,
            status=new_patient.status,
            last_visit_at=new_patient.last_visit_at,
            visit_count=new_patient.visit_count
        )
    
    @staticmethod    
    async def list_patients(
        db: AsyncSession,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 20,
        category: PatientCategoryEnum | None = None,
        status: PatientStatusEnum | None = None,
        gender: GenderEnum | None = None,
        blood_group: BloodGroupEnum | None = None,
    ) -> list[PatientListItem]:
        """List patients for the tenant with pagination"""
        filters = [
            Patient.tenant_id == tenant_id,
            Patient.status != PatientStatusEnum.INACTIVE
        ]

        if category:
            filters.append(Patient.category == category)

        if status:
            filters.append(Patient.status == status)

        if gender:
            filters.append(Patient.gender == gender)

        if blood_group:
            filters.append(Patient.blood_group == blood_group)

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
        patients = result.scalars().all()
        
        if not patients:
            return []
        return [
            PatientListItem(
                id=patient.id,
                patient_code=patient.patient_code,
                first_name=patient.first_name,
                last_name=patient.last_name,
                date_of_birth=patient.date_of_birth,   
                gender=patient.gender,
                blood_group=patient.blood_group,
                phone=patient.phone,
                email=patient.email,
                address=patient.address,
                category=patient.category,
                status=patient.status,
            ) for patient in patients
        ]
        
    @staticmethod
    async def get_patient_by_id(
        db: AsyncSession,
        tenant_id: UUID,
        patient_id: UUID
    ) -> PatientDetail:
        """Get a specific patient by ID"""
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
        patient = result.scalars().first()
        
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        return PatientDetail(
            id=patient.id,
            patient_code=patient.patient_code,
            first_name=patient.first_name,
            last_name=patient.last_name,
            date_of_birth=patient.date_of_birth,
            gender=patient.gender,
            blood_group=patient.blood_group,
            phone=patient.phone,
            email=patient.email,
            address=patient.address,
            category=patient.category,
            status=patient.status,
            visit_count=patient.visit_count,
            last_visit_at=patient.last_visit_at,
            created_by_id=patient.created_by_id,
            updated_by_id=patient.updated_by_id,
            medical_record=MedicalRecordSummary(
                id=patient.medical_record.id,
                patient_id=patient.medical_record.patient_id,
                systemic_conditions=patient.medical_record.systemic_conditions if patient.medical_record.systemic_conditions else None,
                current_medications=patient.medical_record.current_medications if patient.medical_record.current_medications else None,
                prior_surgeries=patient.medical_record.prior_surgeries if patient.medical_record.prior_surgeries else None,
                emergency_contact_name=patient.medical_record.emergency_contact_name if patient.medical_record.emergency_contact_name else None,
                emergency_contact_phone=patient.medical_record.emergency_contact_phone if patient.medical_record.emergency_contact_phone else None, 
                allergies=patient.medical_record.allergies if patient.medical_record else None
            ) if patient.medical_record else None,
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
            PatientListItem(
                id=patient.id,
                patient_code=patient.patient_code,
                first_name=patient.first_name,
                last_name=patient.last_name,
                date_of_birth=patient.date_of_birth,
                gender=patient.gender,
                blood_group=patient.blood_group,
                phone=patient.phone,
                email=patient.email,
                address=patient.address,
                category=patient.category,
                status=patient.status
            ) for patient in patients
        ]
        
    @staticmethod
    async def update_patient(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        patient_id: UUID,
        payload: dict,
    ) -> PatientResponse:
        """Update patient details"""
        query = (
            select(Patient)
            .where(
                Patient.tenant_id == tenant_id,
                Patient.id == patient_id
            )
            .options(
                selectinload(Patient.medical_record)
            )
        )
        result = await db.execute(query)
        patient = result.scalars().first()
        
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        # Update patient fields
        for field, value in payload.items():
            if hasattr(patient, field) and value is not None:
                setattr(patient, field, value)
        patient.updated_by_id = user_id
        patient.updated_at = datetime.now(UTC)
        
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
        return PatientResponse(
            id=patient.id,
            patient_code=patient.patient_code,
            first_name=patient.first_name,
            last_name=patient.last_name,
            date_of_birth=patient.date_of_birth,
            gender=patient.gender,
            blood_group=patient.blood_group,
            phone=patient.phone,
            email=patient.email,
            address=patient.address,
            category=patient.category,
            status=patient.status,  
            visit_count=patient.visit_count,
            last_visit_at=patient.last_visit_at
        )
        
    @staticmethod
    async def delete_patient(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        patient_id: UUID
    ):
        """Soft delete a patient by setting status to INACTIVE"""
        query = (
            select(Patient)
            .where(
                Patient.tenant_id == tenant_id,
                Patient.id == patient_id
            )
        )
        result = await db.execute(query)
        patient = result.scalars().first()
        
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        patient.status = PatientStatusEnum.INACTIVE
        patient.updated_at = datetime.now(UTC)
        patient.updated_by_id = user_id
        
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete patient due to integrity error."
            )