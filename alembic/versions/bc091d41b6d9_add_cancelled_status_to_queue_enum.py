"""add cancelled status to queue enum

Revision ID: bc091d41b6d9
Revises: 88c959ac54c1
Create Date: 2026-05-27 22:48:27.823080

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc091d41b6d9'
down_revision: Union[str, Sequence[str], None] = '88c959ac54c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
