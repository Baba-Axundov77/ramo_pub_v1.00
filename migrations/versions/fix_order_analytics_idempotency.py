"""Fix order_analytics idempotency

Revision ID: fix_order_analytics_idempotency
Revises: 
Create Date: 2024-03-13 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_order_analytics_idempotency'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add unique constraint for idempotency
    op.create_index(
        'ix_order_analytics_order_event_unique',
        'order_analytics',
        ['order_id', 'event_type'],
        unique=True
    )


def downgrade():
    # Remove unique constraint
    op.drop_index(
        'ix_order_analytics_order_event_unique',
        table_name='order_analytics'
    )
