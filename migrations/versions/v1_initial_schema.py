"""initial_schema_v1 - Consolidated Database Schema

This migration consolidates all previous migrations into a single initial schema
for PostgreSQL deployment with proper indexes and constraints.

Revision ID: v1_initial_schema
Revises: 
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "v1_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

# Enums
user_role_enum = postgresql.ENUM("admin", "manager", "waiter", "cashier", "kitchen", name="userrole")
table_status_enum = postgresql.ENUM("available", "occupied", "reserved", "cleaning", name="tablestatus")
order_status_enum = postgresql.ENUM("new", "preparing", "ready", "served", "paid", "cancelled", name="orderstatus")
payment_method_enum = postgresql.ENUM("cash", "card", "online", name="paymentmethod")

def upgrade() -> None:
    # Create enums
    user_role_enum.create(op.get_bind(), checkfirst=True)
    table_status_enum.create(op.get_bind(), checkfirst=True)
    order_status_enum.create(op.get_bind(), checkfirst=True)
    payment_method_enum.create(op.get_bind(), checkfirst=True)

    # Users table with optimized indexes
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=50), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column("password", sa.String(length=255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    # Performance indexes for User table
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_role_is_active", "users", ["role", "is_active"])

    # Tables table
    op.create_table(
        "tables",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("number", sa.Integer(), nullable=False, unique=True),
        sa.Column("name", sa.String(length=50), nullable=True),
        sa.Column("capacity", sa.Integer(), default=4, nullable=False),
        sa.Column("status", table_status_enum, default="available", nullable=False),
        sa.Column("floor", sa.Integer(), default=1, nullable=False),
        sa.Column("zone", sa.String(length=50), nullable=True),
        sa.Column("current_order_id", sa.Integer(), nullable=True),
        sa.Column("image_path", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.ForeignKeyConstraint(["current_order_id"], ["orders.id"]),
    )
    op.create_index("ix_tables_number", "tables", ["number"], unique=True)
    op.create_index("ix_tables_status_floor", "tables", ["status", "floor"])

    # Menu Categories
    op.create_table(
        "menu_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("name_az", sa.String(length=100), nullable=True),
        sa.Column("name_en", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(length=50), nullable=True),
        sa.Column("sort_order", sa.Integer(), default=0, nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["menu_categories.id"]),
    )
    op.create_index("ix_categories_parent_sort", "menu_categories", ["parent_id", "sort_order"])

    # Inventory Items (for recipe costing)
    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("current_stock", sa.Float(), default=0.0, nullable=False),
        sa.Column("min_quantity", sa.Float(), default=5.0, nullable=False),
        sa.Column("cost_per_unit", sa.Float(), default=0.0, nullable=False),
        sa.Column("supplier", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    # Performance indexes for Inventory
    op.create_index("ix_inventory_items_name", "inventory_items", ["name"])
    op.create_index("ix_inventory_items_active_stock", "inventory_items", ["is_active", "current_stock"])

    # Menu Items with all required fields
    op.create_table(
        "menu_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("cost_price", sa.Float(), default=0.0, nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("image_path", sa.String(length=255), nullable=True),
        sa.Column("prep_time_min", sa.Integer(), default=0, nullable=False),
        sa.Column("inventory_item_id", sa.Integer(), nullable=True),
        sa.Column("kitchen_station_id", sa.Integer(), nullable=True),
        sa.Column("stock_usage_qty", sa.Float(), default=0.0, nullable=False),
        sa.Column("sort_order", sa.Integer(), default=0, nullable=False),
        sa.Column("is_available", sa.Boolean(), default=True, nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["menu_categories.id"]),
        sa.ForeignKeyConstraint(["inventory_item_id"], ["inventory_items.id"]),
    )
    op.create_index("ix_menu_items_category_active", "menu_items", ["category_id", "is_active"])
    op.create_index("ix_menu_items_available_sort", "menu_items", ["is_available", "sort_order"])

    # Orders table with performance indexes
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("table_id", sa.Integer(), nullable=True),
        sa.Column("waiter_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("status", order_status_enum, default="new", nullable=False),
        sa.Column("subtotal", sa.Float(), default=0.0, nullable=False),
        sa.Column("total_amount", sa.Float(), default=0.0, nullable=False),
        sa.Column("discount_amount", sa.Float(), default=0.0, nullable=False),
        sa.Column("total", sa.Float(), default=0.0, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"]),
        sa.ForeignKeyConstraint(["waiter_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
    )
    # Performance indexes for Order table
    op.create_index("ix_orders_created_at_status", "orders", ["created_at", "status"])
    op.create_index("ix_orders_table_id_status_created_at", "orders", ["table_id", "status", "created_at"])
    op.create_index("ix_orders_waiter_id_created_at", "orders", ["waiter_id", "created_at"])

    # Order Items
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("menu_item_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("total_price", sa.Float(), nullable=False),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu_items.id"]),
    )
    op.create_index("ix_order_items_order_menu", "order_items", ["order_id", "menu_item_id"])

    # Payments
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("method", payment_method_enum, nullable=False),
        sa.Column("discount_amount", sa.Float(), default=0.0, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
    )
    op.create_index("ix_payments_order_created", "payments", ["order_id", "created_at"])

    # Customers (for loyalty system)
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("loyalty_points", sa.Integer(), default=0, nullable=False),
        sa.Column("total_spent", sa.Float(), default=0.0, nullable=False),
        sa.Column("visit_count", sa.Integer(), default=0, nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_customers_phone", "customers", ["phone"])
    op.create_index("ix_customers_email", "customers", ["email"])
    op.create_index("ix_customers_loyalty_active", "customers", ["loyalty_points", "is_active"])

    # Menu Item Recipes (for recipe costing)
    op.create_table(
        "menu_item_recipes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("menu_item_id", sa.Integer(), nullable=False),
        sa.Column("inventory_item_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("quantity_unit", sa.String(length=30), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inventory_item_id"], ["inventory_items.id"]),
    )
    op.create_index("ix_recipes_menu_active", "menu_item_recipes", ["menu_item_id", "is_active"])

    # Kitchen Stations (for KDS)
    op.create_table(
        "kitchen_stations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )

    # Reservations
    op.create_table(
        "reservations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("table_id", sa.Integer(), nullable=False),
        sa.Column("reservation_time", sa.DateTime(), nullable=False),
        sa.Column("party_size", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), default="confirmed", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"]),
    )
    op.create_index("ix_reservations_time_status", "reservations", ["reservation_time", "status"])
    op.create_index("ix_reservations_table_time", "reservations", ["table_id", "reservation_time"])

def downgrade() -> None:
    # Drop tables in reverse order to handle foreign key constraints
    op.drop_table("reservations")
    op.drop_table("kitchen_stations")
    op.drop_table("menu_item_recipes")
    op.drop_table("customers")
    op.drop_table("payments")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("menu_items")
    op.drop_table("inventory_items")
    op.drop_table("menu_categories")
    op.drop_table("tables")
    op.drop_table("users")
    
    # Drop enums
    user_role_enum.drop(op.get_bind())
    table_status_enum.drop(op.get_bind())
    order_status_enum.drop(op.get_bind())
    payment_method_enum.drop(op.get_bind())
