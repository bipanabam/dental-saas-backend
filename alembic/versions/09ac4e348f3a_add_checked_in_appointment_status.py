"""add checked_in appointment status

Revision ID: 09ac4e348f3a
Revises: bc091d41b6d9
Create Date: 2026-05-28 14:17:06.255841

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '09ac4e348f3a'
down_revision: Union[str, Sequence[str], None] = 'bc091d41b6d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        ALTER TYPE appointment_status_enum
        ADD VALUE IF NOT EXISTS 'CHECKED_IN';
        """
    )
    op.execute(
        """
        ALTER TYPE appointment_type_enum
        ADD VALUE IF NOT EXISTS 'RESCHEDULED';
        """
    )
    op.execute(
        """
        ALTER TYPE queue_status_enum
        ADD VALUE IF NOT EXISTS 'CANCELLED';
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
