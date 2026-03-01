"""schema alignment and role expansion

Revision ID: 0002_schema_alignment
Revises: 0001_baseline
Create Date: 2026-03-01
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_schema_alignment"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns(table)}
    if column.name not in cols:
        op.add_column(table, column)


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'manager'")
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'kitchen'")

    _add_column_if_missing("tables", sa.Column("zone", sa.String(length=50), nullable=True))
    _add_column_if_missing("tables", sa.Column("current_order_id", sa.Integer(), nullable=True))

    _add_column_if_missing("menu_categories", sa.Column("name_az", sa.String(length=100), nullable=True))
    _add_column_if_missing("menu_categories", sa.Column("name_en", sa.String(length=100), nullable=True))
    _add_column_if_missing("menu_categories", sa.Column("parent_id", sa.Integer(), nullable=True))

    _add_column_if_missing("menu_items", sa.Column("image_url", sa.Text(), nullable=True))
    _add_column_if_missing("menu_items", sa.Column("prep_time_min", sa.Integer(), nullable=True, server_default="0"))

    _add_column_if_missing("orders", sa.Column("total_amount", sa.Float(), nullable=True, server_default="0.0"))
    _add_column_if_missing("orders", sa.Column("note", sa.Text(), nullable=True))
    _add_column_if_missing("orders", sa.Column("closed_at", sa.DateTime(), nullable=True))

    _add_column_if_missing("order_items", sa.Column("note", sa.Text(), nullable=True))
    _add_column_if_missing("order_items", sa.Column("sent_to_kitchen_at", sa.DateTime(), nullable=True))

    _add_column_if_missing("payments", sa.Column("paid_at", sa.DateTime(), nullable=True))

    _add_column_if_missing("reservations", sa.Column("reserved_at", sa.DateTime(), nullable=True))
    _add_column_if_missing("reservations", sa.Column("status", sa.String(length=20), nullable=True, server_default="pending"))


def downgrade() -> None:
    for table, col in [
        ("reservations", "status"),
        ("reservations", "reserved_at"),
        ("payments", "paid_at"),
        ("order_items", "sent_to_kitchen_at"),
        ("order_items", "note"),
        ("orders", "closed_at"),
        ("orders", "note"),
        ("orders", "total_amount"),
        ("menu_items", "prep_time_min"),
        ("menu_items", "image_url"),
        ("menu_categories", "parent_id"),
        ("menu_categories", "name_en"),
        ("menu_categories", "name_az"),
        ("tables", "current_order_id"),
        ("tables", "zone"),
    ]:
        try:
            op.drop_column(table, col)
        except Exception:
            pass
