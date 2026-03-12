"""merge_heads_for_sqlalchemy_2_0

Revision ID: ac94508acf75
Revises: 10ea20f3a185, v1_initial_schema
Create Date: 2026-03-10 09:24:28.463852

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac94508acf75'
down_revision: Union[str, Sequence[str], None] = ('10ea20f3a185', 'v1_initial_schema')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
