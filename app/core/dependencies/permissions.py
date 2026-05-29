from fastapi import Depends, HTTPException, status

from app.core.dependencies.auth import CurrentAuth

def require_permissions(*permissions: str):

    async def checker(
        auth: CurrentAuth,
    ):

        role_permissions = {
            rp.permission.name
            for rp in auth.membership.role.permissions
        }

        if "*" in role_permissions:
            return

        if not any(
            permission in role_permissions
            for permission in permissions
        ):
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions",
            )

    return Depends(checker)

CanReadUsers = require_permissions("staff.read")
CanCreateUsers = require_permissions("staff.create")
CanUpdateUsers = require_permissions("staff.update")
CanDeleteUsers = require_permissions("staff.delete")

# Patients
CanReadPatients = require_permissions("patients.read")
CanCreatePatients = require_permissions("patients.create")
CanUpdatePatients = require_permissions("patients.update") 
CanDeletePatients = require_permissions("patients.delete")

# Appointments
CanCreateAppointments = require_permissions("appointments.create")
CanReadAppointments = require_permissions("appointments.read")
CanUpdateAppointments = require_permissions("appointments.update")
CanDeleteAppointments = require_permissions("appointments.delete")
CanCheckInAppointments = require_permissions("appointments.checkin")
CanCompleteAppointments = require_permissions("appointments.complete")

# Queue
CanCreateQueue = require_permissions("queue.create")
CanReadQueue = require_permissions("queue.read")
CanUpdateQueue = require_permissions("queue.update")
CanDeleteQueue = require_permissions("queue.delete")