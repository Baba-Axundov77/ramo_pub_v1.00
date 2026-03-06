"""add soft-delete flags for maintainability and safe archival

Revision ID: 0005_add_soft_delete_flags
Revises: 0004_add_performance_indexes
Create Date: 2026-03-06
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_add_soft_delete_flags"
down_revision = "0004_add_performance_indexes"
branch_labels = None
depends_on = None


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns(table)}
    if column.name not in cols:
        op.add_column(table, column)


def upgrade() -> None:
    _add_column_if_missing("inventory_items", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")))
    _add_column_if_missing("customers", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")))
    _add_column_if_missing("shifts", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")))
    _add_column_if_missing("purchase_receipts", sa.Column("is_cancelled", sa.Boolean(), nullable=False, server_default=sa.text("0")))


def downgrade() -> None:
    for table, col in [
        ("purchase_receipts", "is_cancelled"),
        ("shifts", "is_active"),
        ("customers", "is_active"),
        ("inventory_items", "is_active"),
    ]:
        try:
            op.drop_column(table, col)
        except Exception:
            pass
