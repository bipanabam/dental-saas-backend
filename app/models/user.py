# User, Role, Permission
import enum
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BaseMixin

class Membership(Base, BaseMixin):
    __tablename__ = "memberships"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE")
    )
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"))
    
        
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    joined_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="memberships")
    tenant = relationship("Tenant", back_populates="users")
    role = relationship(
        "Role",
        back_populates="memberships"
    )
    user_preference = relationship(
        "UserPreference",
        back_populates="membership",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_memberships_user_id", "user_id"),
        Index("ix_memberships_tenant_id", "tenant_id"),
        Index("ix_memberships_role_id", "role_id"),
        UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant_membership"),
    )


class Role(Base, BaseMixin):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50))  # admin, manager, custom
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )

    permissions = relationship("RolePermission", back_populates="role")
    memberships = relationship("Membership", back_populates="role")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_role_name_per_tenant"),
        Index(
            "uq_global_roles_name",
            "name",
            unique=True,
            postgresql_where=(tenant_id.is_(None)),
        ),
    )


class RolePermission(Base, BaseMixin):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True
    )

    permission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True
    )

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission")


class Permission(Base, BaseMixin):
    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(
        String(100), unique=True
    )  # "create_user", "view_reports"
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    
    roles = relationship("RolePermission", back_populates="permission")


class User(Base, BaseMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    last_login_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    avatar_url: Mapped[str] = mapped_column(String(500), nullable=True)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=True)

    memberships = relationship("Membership", back_populates="user")
class UserSession(Base, BaseMixin):
    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )

    refresh_token_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    revoked_at : Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    expires_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    user = relationship("User")
    
class UserPreference(Base, BaseMixin):
    __tablename__ = "user_preferences"

    membership_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("memberships.id"),
        unique=True
    )

    notify_appointment: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_waiting: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_lab_results: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_draft_reminder: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_daily_summary: Mapped[bool] = mapped_column(Boolean, default=False)

    require_otp: Mapped[bool] = mapped_column(Boolean, default=False)
    
    membership = relationship("Membership", back_populates="user_preference")

# class DoctorProfile(Base, BaseMixin):
#     __tablename__ = "doctor_profiles"

#     membership_id: Mapped[uuid.UUID] = mapped_column(
#         ForeignKey("memberships.id")
#     )

#     specialization: Mapped[str] = mapped_column(String(255), nullable=True)
#     nmc_reg_no: Mapped[str] = mapped_column(String(100), nullable=True)
#     qualification: Mapped[str] = mapped_column(String(255), nullable=True)
#     experience_years: Mapped[int] = mapped_column(Integer, nullable=True)