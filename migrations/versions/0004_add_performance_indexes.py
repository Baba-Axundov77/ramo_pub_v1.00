"""add performance indexes for hot query paths

Revision ID: 0004_add_performance_indexes
Revises: 0003_purchase_receipts_and_menu_inventory_link
Create Date: 2026-03-06
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_add_performance_indexes"
down_revision = "0003_purchase_receipts_and_menu_inventory_link"
branch_labels = None
depends_on = None


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    indexes = insp.get_indexes(table_name)
    return any(idx.get("name") == index_name for idx in indexes)


def upgrade() -> None:
    if not _index_exists("orders", "ix_orders_created_at_status"):
        op.create_index(
            "ix_orders_created_at_status",
            "orders",
            ["created_at", "status"],
            unique=False,
        )

    if not _index_exists("orders", "ix_orders_table_id_status_created_at"):
        op.create_index(
            "ix_orders_table_id_status_created_at",
            "orders",
            ["table_id", "status", "created_at"],
            unique=False,
        )

    if not _index_exists("payments", "ix_payments_created_at_method"):
        op.create_index(
            "ix_payments_created_at_method",
            "payments",
            ["created_at", "method"],
            unique=False,
        )

    if not _index_exists("reservations", "ix_reservations_date_table_id_is_cancelled"):
        op.create_index(
            "ix_reservations_date_table_id_is_cancelled",
            "reservations",
            ["date", "table_id", "is_cancelled"],
            unique=False,
        )


def downgrade() -> None:
    for table_name, index_name in [
        ("reservations", "ix_reservations_date_table_id_is_cancelled"),
        ("payments", "ix_payments_created_at_method"),
        ("orders", "ix_orders_table_id_status_created_at"),
        ("orders", "ix_orders_created_at_status"),
    ]:
        if _index_exists(table_name, index_name):
            op.drop_index(index_name, table_name=table_name)
