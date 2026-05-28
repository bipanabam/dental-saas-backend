"""update family relationship enum

Revision ID: 9cda94581a1c
Revises: 964664688026
Create Date: 2026-05-28 18:49:06.350762

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9cda94581a1c'
down_revision: Union[str, Sequence[str], None] = '964664688026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    values = [
        "HUSBAND",
        "WIFE",
        "FATHER",
        "MOTHER",
        "SON",
        "DAUGHTER",
        "BROTHER",
        "SISTER",
        "GRANDPARENT",
        "GRANDCHILD",
    ]

    for value in values:
        op.execute(
            f"""
            ALTER TYPE family_relationship_enum
            ADD VALUE IF NOT EXISTS '{value}';
            """
        )


def downgrade() -> None:
    """Downgrade schema."""
    pass
