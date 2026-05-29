from datetime import datetime, date
import uuid

from sqlalchemy import (
    Enum,
    ForeignKey,
    UniqueConstraint,
    DateTime
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BaseMixin
from app.utils.enums import (
    QueueStatusEnum
)

class Queue(Base, BaseMixin):
    __tablename__ = "queues"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    queue_date: Mapped[date]
    token_number: Mapped[int]
    chair_number: Mapped[int | None]
    estimated_wait_mins: Mapped[int | None]
    priority: Mapped[int] = mapped_column(default=0)

    status: Mapped[QueueStatusEnum] = mapped_column(
        Enum(QueueStatusEnum, name="queue_status_enum"),
        default=QueueStatusEnum.WAITING,
    )

    called_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    appointment = relationship(
        "Appointment",
        back_populates="queue_entry",
    )
    
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "queue_date",
            "token_number",
            name="uq_queue_token_per_day",
        ),
    )
    
    
# queue.mark_skipped()
# queue.mark_waiting()
# queue.mark_in_progress()
# queue.mark_completed()