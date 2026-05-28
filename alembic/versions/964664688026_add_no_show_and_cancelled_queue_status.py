"""add no_show and cancelled queue status

Revision ID: 964664688026
Revises: 09ac4e348f3a
Create Date: 2026-05-28 14:45:15.889771

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '964664688026'
down_revision: Union[str, Sequence[str], None] = '09ac4e348f3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        ALTER TYPE queue_status_enum
        ADD VALUE IF NOT EXISTS 'COMPLETED';
        """
    )
    op.execute(
        """
        ALTER TYPE queue_status_enum
        ADD VALUE IF NOT EXISTS 'NO_SHOW';
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
