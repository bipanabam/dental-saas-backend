from datetime import datetime, UTC
from uuid import UUID

from app.models import ClinicalEncounter, TreatmentPlanItem, Procedure

from app.schemas.encounter import TreatmentPlanItemPerformCreate

from app.utils.enums import ProcedureStatusEnum

class ProcedureFactory:

    @staticmethod
    def from_plan_item(
        item: TreatmentPlanItem,
        encounter: ClinicalEncounter,
        performed_by_id: UUID,
        payload: TreatmentPlanItemPerformCreate,
    ) -> Procedure:

        now = datetime.now(UTC)

        return Procedure(
            tenant_id=encounter.tenant_id,
            patient_id=encounter.patient_id,
            appointment_id=encounter.appointment_id,
            encounter_id=encounter.id,

            procedure_catalog_id=item.procedure_catalog_id,

            tooth_numbers=item.tooth_numbers,

            status=ProcedureStatusEnum.COMPLETED,

            estimated_cost=item.estimated_cost,

            final_cost=(
                payload.final_cost
                or item.estimated_cost
            ),

            performed_by_id=performed_by_id,

            performed_duration_minutes=(
                payload.performed_duration_minutes
            ),

            procedure_date=now,
            completed_at=now,
        )