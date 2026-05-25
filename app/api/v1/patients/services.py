from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.models.medical_record import MedicalRecord
from app.schemas.patient import PatientResponse
from app.utils.patient_code import generate_patient_code


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
            visit_count=new_patient.visit_count,
            last_visit_at=new_patient.last_visit_at.isoformat() if new_patient.last_visit_at else None,
            allergies=medical_record.allergies, # include allergies from medical record
            created_by_id=str(new_patient.created_by_id) if new_patient.created_by_id else None,
            updated_by_id=str(new_patient.updated_by_id) if new_patient.updated_by_id else None
        )