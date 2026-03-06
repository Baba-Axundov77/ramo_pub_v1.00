"""purchase receipts and menu inventory link

Revision ID: 0003_purchase_receipts_and_menu_inventory_link
Revises: 0002_schema_alignment
Create Date: 2026-03-02
"""
from alembic import op
import sqlalchemy as sa

revision = '0003_purchase_receipts_and_menu_inventory_link'
down_revision = '0002_schema_alignment'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # menu_items.inventory_item_id — yalnız yoxdursa əlavə et
    existing = {c["name"] for c in insp.get_columns("menu_items")}
    if "inventory_item_id" not in existing:
        op.add_column('menu_items', sa.Column('inventory_item_id', sa.Integer(), nullable=True))
        if bind.dialect.name != "sqlite":
            op.create_foreign_key('fk_menu_items_inventory_item_id', 'menu_items', 'inventory_items', ['inventory_item_id'], ['id'])

    # purchase_receipts — yalnız yoxdursa yarat
    tables = insp.get_table_names()
    if "purchase_receipts" not in tables:
        op.create_table(
            'purchase_receipts',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('purchased_at', sa.DateTime(), nullable=False),
            sa.Column('store_name', sa.String(length=120), nullable=True),
            sa.Column('note', sa.Text(), nullable=True),
            sa.Column('total_amount', sa.Float(), nullable=False, server_default='0'),
            sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        )

    if "purchase_receipt_items" not in tables:
        op.create_table(
            'purchase_receipt_items',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('receipt_id', sa.Integer(), sa.ForeignKey('purchase_receipts.id'), nullable=False),
            sa.Column('inventory_item_id', sa.Integer(), sa.ForeignKey('inventory_items.id'), nullable=False),
            sa.Column('item_name', sa.String(length=150), nullable=False),
            sa.Column('unit', sa.String(length=30), nullable=False),
            sa.Column('quantity', sa.Float(), nullable=False),
            sa.Column('unit_cost', sa.Float(), nullable=False),
            sa.Column('line_total', sa.Float(), nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_table('purchase_receipt_items')
    op.drop_table('purchase_receipts')
    if bind.dialect.name != "sqlite":
        op.drop_constraint('fk_menu_items_inventory_item_id', 'menu_items', type_='foreignkey')
    op.drop_column('menu_items', 'inventory_item_id')
