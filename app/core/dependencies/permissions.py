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