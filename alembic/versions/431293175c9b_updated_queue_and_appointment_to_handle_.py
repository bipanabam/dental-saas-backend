"""Updated Queue and Appointment to handle cancel appointment

Revision ID: 431293175c9b
Revises: 911000fbc360
Create Date: 2026-05-27 22:30:33.923070
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = "431293175c9b"
down_revision: Union[str, Sequence[str], None] = "911000fbc360"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# DEFINE ENUM SEPARATELY
appointment_cancellation_reason_enum = sa.Enum(
    "PATIENT_CANCELLED",
    "DOCTOR_UNAVAILABLE",
    "NO_SHOW",
    "RESCHEDULED",
    "DUPLICATE_BOOKING",
    "EMERGENCY",
    "OTHER",
    name="appointment_cancellation_reason_enum",
)


def upgrade() -> None:
    """Upgrade schema."""

    # CREATE ENUM TYPE FIRST
    appointment_cancellation_reason_enum.create(
        op.get_bind(),
        checkfirst=True,
    )

    # APPOINTMENTS
    op.add_column(
        "appointments",
        sa.Column(
            "cancellation_reason_type",
            appointment_cancellation_reason_enum,
            nullable=True,
        ),
    )

    op.add_column(
        "appointments",
        sa.Column(
            "cancellation_reason_note",
            sa.Text(),
            nullable=True,
        ),
    )

    op.drop_column(
        "appointments",
        "cancellation_reason",
    )

    # QUEUES
    op.add_column(
        "queues",
        sa.Column(
            "cancelled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_unique_constraint(
        "uq_queue_token_per_day",
        "queues",
        ["tenant_id", "queue_date", "token_number"],
    )


def downgrade() -> None:
    """Downgrade schema."""

    # DROP CONSTRAINT
    op.drop_constraint(
        "uq_queue_token_per_day",
        "queues",
        type_="unique",
    )

    # QUEUES
    op.drop_column(
        "queues",
        "cancelled_at",
    )

    # RESTORE OLD COLUMN
    op.add_column(
        "appointments",
        sa.Column(
            "cancellation_reason",
            sa.Text(),
            nullable=True,
        ),
    )

    # REMOVE NEW COLUMNS
    op.drop_column(
        "appointments",
        "cancellation_reason_note",
    )

    op.drop_column(
        "appointments",
        "cancellation_reason_type",
    )

    # DROP ENUM TYPE
    appointment_cancellation_reason_enum.drop(
        op.get_bind(),
        checkfirst=True,
    )