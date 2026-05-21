from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth.schemas import (
    Register,
    RegisterTenantResponse,
)

from app.core.security import hash_password

from app.models import (
    Membership,
    Role,
    Subscription,
    SubscriptionStatus,
    Tenant,
    User,
)
from app.models.tenant import PlanEnum


TRIAL_DAYS = 14


async def register_tenant_service(
    db: AsyncSession,
    payload: Register,
) -> RegisterTenantResponse:

    # Check Existing Tenant
    existing_tenant_result = await db.execute(
        select(Tenant).where(
            Tenant.slug == payload.slug
        )
    )

    existing_tenant = (
        existing_tenant_result.scalar_one_or_none()
    )

    if existing_tenant:
        raise ValueError("Tenant slug already exists.")

    # Check Existing User
    existing_user_result = await db.execute(
        select(User).where(
            User.email == payload.email
        )
    )

    existing_user = (
        existing_user_result.scalar_one_or_none()
    )

    if existing_user:
        raise ValueError("Email already exists.")
    
    # Create Tenant
    tenant = Tenant(
        name=payload.name,
        slug=payload.slug,
        is_active=True,
    )

    db.add(tenant)

    await db.flush()

    # Create Subscription
    now = datetime.now(UTC)

    subscription = Subscription(
        tenant_id=tenant.id,
        plan=PlanEnum.BASIC,
        status=SubscriptionStatus.TRIAL,
        start_date=now,
        end_date=now + timedelta(days=TRIAL_DAYS),
        auto_renew=False,
    )

    db.add(subscription)

    # Create Owner User
    user = User(
        email=payload.email,
        username=payload.email.split("@")[0],
        hashed_password=hash_password(payload.password),
        is_active=True,
        is_verified=False,
    )

    db.add(user)
    await db.flush()


    # Get Admin Role
    role_result = await db.execute(
        select(Role).where(
            Role.name == "admin",
            Role.tenant_id.is_(None),
        )
    )

    admin_role = role_result.scalar_one_or_none()

    if not admin_role:
        raise ValueError(
            "Admin role not seeded."
        )

    # Create Membership
    membership = Membership(
        user_id=user.id,
        tenant_id=tenant.id,
        role_id=admin_role.id,
        is_active=True,
    )

    db.add(membership)


    # Commit Transaction
    try:
        await db.commit()

    except IntegrityError:
        await db.rollback()
        raise


    # Refresh Entities
    await db.refresh(tenant)

    return RegisterTenantResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
        owner_email=user.email,
        subscription_plan=subscription.plan,
        subscription_status=subscription.status,
    )