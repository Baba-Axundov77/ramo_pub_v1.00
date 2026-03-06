"""catchup: add all missing columns from 0002-0005 that were never applied to the live DB

Revision ID: 0006_catchup_missing_columns
Revises: 0005_add_soft_delete_flags
Create Date: 2026-03-06
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_catchup_missing_columns"
down_revision = "0005_add_soft_delete_flags"
branch_labels = None
depends_on = None


def _col_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return column in {c["name"] for c in insp.get_columns(table)}


def _index_exists(table: str, index: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return any(i.get("name") == index for i in insp.get_indexes(table))


def _add(table: str, col: sa.Column) -> None:
    if not _col_exists(table, col.name):
        op.add_column(table, col)


def upgrade() -> None:
    bind = op.get_bind()

    # ── userrole enum genişlənməsi (0002-dən) ─────────────────────────────
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'manager'")
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'kitchen'")

    # ── tables (0002-dən) ─────────────────────────────────────────────────
    _add("tables", sa.Column("name",             sa.String(50),  nullable=True))
    _add("tables", sa.Column("floor",            sa.Integer(),   nullable=True, server_default="1"))
    _add("tables", sa.Column("zone",             sa.String(50),  nullable=True))
    _add("tables", sa.Column("current_order_id", sa.Integer(),   nullable=True))
    _add("tables", sa.Column("image_path",       sa.String(255), nullable=True))

    # ── menu_categories (0002-dən) ────────────────────────────────────────
    _add("menu_categories", sa.Column("name_az",   sa.String(100), nullable=True))
    _add("menu_categories", sa.Column("name_en",   sa.String(100), nullable=True))
    _add("menu_categories", sa.Column("parent_id", sa.Integer(),   nullable=True))

    # ── menu_items (0002 + 0003-dən) ──────────────────────────────────────
    _add("menu_items", sa.Column("image_url",          sa.Text(),    nullable=True))
    _add("menu_items", sa.Column("prep_time_min",      sa.Integer(), nullable=True, server_default="0"))
    _add("menu_items", sa.Column("inventory_item_id",  sa.Integer(), nullable=True))
    _add("menu_items", sa.Column("stock_usage_qty",    sa.Float(),   nullable=True, server_default="0.0"))
    _add("menu_items", sa.Column("sort_order",         sa.Integer(), nullable=True, server_default="0"))

    # ── menu_item_recipes (0002-dən) ──────────────────────────────────────
    _add("menu_item_recipes", sa.Column("quantity_unit", sa.String(30),  nullable=True))
    _add("menu_item_recipes", sa.Column("valid_from",    sa.Date(),       nullable=True))
    _add("menu_item_recipes", sa.Column("valid_until",   sa.Date(),       nullable=True))
    _add("menu_item_recipes", sa.Column("is_active",     sa.Boolean(),    nullable=True, server_default=sa.text("true")))
    _add("menu_item_recipes", sa.Column("created_at",    sa.DateTime(),   nullable=True))

    # ── orders (0002-dən) ─────────────────────────────────────────────────
    _add("orders", sa.Column("total_amount",    sa.Float(),  nullable=True, server_default="0.0"))
    _add("orders", sa.Column("note",            sa.Text(),   nullable=True))
    _add("orders", sa.Column("notes",           sa.Text(),   nullable=True))
    _add("orders", sa.Column("closed_at",       sa.DateTime(), nullable=True))
    _add("orders", sa.Column("updated_at",      sa.DateTime(), nullable=True))

    # ── order_items (0002-dən) ────────────────────────────────────────────
    _add("order_items", sa.Column("note",              sa.Text(),     nullable=True))
    _add("order_items", sa.Column("sent_to_kitchen_at", sa.DateTime(), nullable=True))

    # ── payments (0002-dən) ───────────────────────────────────────────────
    _add("payments", sa.Column("paid_at",          sa.DateTime(), nullable=True))
    _add("payments", sa.Column("discount_amount",  sa.Float(),    nullable=True, server_default="0.0"))

    # ── reservations (0002-dən) ───────────────────────────────────────────
    _add("reservations", sa.Column("reserved_at", sa.DateTime(),  nullable=True))
    _add("reservations", sa.Column("status",      sa.String(20),  nullable=True, server_default="pending"))

    # ── users (0002-dən) ──────────────────────────────────────────────────
    _add("users", sa.Column("phone",      sa.String(20),  nullable=True))
    _add("users", sa.Column("updated_at", sa.DateTime(),  nullable=True))

    # ── inventory_items (0005-dən) ────────────────────────────────────────
    _add("inventory_items", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))

    # ── customers (0005-dən) ──────────────────────────────────────────────
    _add("customers", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))

    # ── shifts (0005-dən) ─────────────────────────────────────────────────
    _add("shifts", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))

    # ── purchase_receipts (0005-dən) ──────────────────────────────────────
    _add("purchase_receipts", sa.Column("is_cancelled", sa.Boolean(), nullable=False, server_default=sa.text("false")))

    # ── Performance indexes (0004-dən) ────────────────────────────────────
    if not _index_exists("orders", "ix_orders_created_at_status"):
        op.create_index("ix_orders_created_at_status", "orders", ["created_at", "status"])
    if not _index_exists("orders", "ix_orders_table_id_status_created_at"):
        op.create_index("ix_orders_table_id_status_created_at", "orders", ["table_id", "status", "created_at"])
    if not _index_exists("payments", "ix_payments_created_at_method"):
        op.create_index("ix_payments_created_at_method", "payments", ["created_at", "method"])
    if not _index_exists("reservations", "ix_reservations_date_table_id_is_cancelled"):
        op.create_index("ix_reservations_date_table_id_is_cancelled", "reservations", ["date", "table_id", "is_cancelled"])

    # ── Soft-delete indexes (0005-dən) ────────────────────────────────────
    if not _index_exists("inventory_items", "ix_inventory_items_is_active"):
        op.create_index("ix_inventory_items_is_active", "inventory_items", ["is_active"])
    if not _index_exists("customers", "ix_customers_is_active"):
        op.create_index("ix_customers_is_active", "customers", ["is_active"])
    if not _index_exists("shifts", "ix_shifts_is_active"):
        op.create_index("ix_shifts_is_active", "shifts", ["is_active"])
    if not _index_exists("purchase_receipts", "ix_purchase_receipts_is_cancelled"):
        op.create_index("ix_purchase_receipts_is_cancelled", "purchase_receipts", ["is_cancelled"])


def downgrade() -> None:
    # Indexes
    for table, idx in [
        ("purchase_receipts",  "ix_purchase_receipts_is_cancelled"),
        ("shifts",             "ix_shifts_is_active"),
        ("customers",          "ix_customers_is_active"),
        ("inventory_items",    "ix_inventory_items_is_active"),
        ("reservations",       "ix_reservations_date_table_id_is_cancelled"),
        ("payments",           "ix_payments_created_at_method"),
        ("orders",             "ix_orders_table_id_status_created_at"),
        ("orders",             "ix_orders_created_at_status"),
    ]:
        try:
            if _index_exists(table, idx):
                op.drop_index(idx, table_name=table)
        except Exception:
            pass

    # Columns
    for table, col in [
        ("purchase_receipts",  "is_cancelled"),
        ("shifts",             "is_active"),
        ("customers",          "is_active"),
        ("inventory_items",    "is_active"),
        ("users",              "updated_at"),
        ("users",              "phone"),
        ("reservations",       "status"),
        ("reservations",       "reserved_at"),
        ("payments",           "discount_amount"),
        ("payments",           "paid_at"),
        ("order_items",        "sent_to_kitchen_at"),
        ("order_items",        "note"),
        ("orders",             "updated_at"),
        ("orders",             "notes"),
        ("orders",             "note"),
        ("orders",             "closed_at"),
        ("orders",             "total_amount"),
        ("menu_item_recipes",  "created_at"),
        ("menu_item_recipes",  "is_active"),
        ("menu_item_recipes",  "valid_until"),
        ("menu_item_recipes",  "valid_from"),
        ("menu_item_recipes",  "quantity_unit"),
        ("menu_items",         "sort_order"),
        ("menu_items",         "stock_usage_qty"),
        ("menu_items",         "inventory_item_id"),
        ("menu_items",         "prep_time_min"),
        ("menu_items",         "image_url"),
        ("menu_categories",    "parent_id"),
        ("menu_categories",    "name_en"),
        ("menu_categories",    "name_az"),
        ("tables",             "image_path"),
        ("tables",             "current_order_id"),
        ("tables",             "zone"),
        ("tables",             "floor"),
        ("tables",             "name"),
    ]:
        try:
            op.drop_column(table, col)
        except Exception:
            pass
