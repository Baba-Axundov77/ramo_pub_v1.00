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


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    indexes = insp.get_indexes(table_name)
    return any(idx.get("name") == index_name for idx in indexes)


def upgrade() -> None:
    _add_column_if_missing("inventory_items", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    _add_column_if_missing("customers", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    _add_column_if_missing("shifts", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    _add_column_if_missing("purchase_receipts", sa.Column("is_cancelled", sa.Boolean(), nullable=False, server_default=sa.text("false")))

    if not _index_exists("inventory_items", "ix_inventory_items_is_active"):
        op.create_index("ix_inventory_items_is_active", "inventory_items", ["is_active"], unique=False)
    if not _index_exists("customers", "ix_customers_is_active"):
        op.create_index("ix_customers_is_active", "customers", ["is_active"], unique=False)
    if not _index_exists("shifts", "ix_shifts_is_active"):
        op.create_index("ix_shifts_is_active", "shifts", ["is_active"], unique=False)
    if not _index_exists("purchase_receipts", "ix_purchase_receipts_is_cancelled"):
        op.create_index("ix_purchase_receipts_is_cancelled", "purchase_receipts", ["is_cancelled"], unique=False)


def downgrade() -> None:
    for table, idx in [
        ("purchase_receipts", "ix_purchase_receipts_is_cancelled"),
        ("shifts", "ix_shifts_is_active"),
        ("customers", "ix_customers_is_active"),
        ("inventory_items", "ix_inventory_items_is_active"),
    ]:
        try:
            if _index_exists(table, idx):
                op.drop_index(idx, table_name=table)
        except Exception:
            pass


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
