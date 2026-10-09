"""add purchase order purchasing documents

Revision ID: 4b7c2d9e1f50
Revises: 3a8f6e2b1c40
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "4b7c2d9e1f50"
down_revision = "3a8f6e2b1c40"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "purchase_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("po_number", sa.String(length=40), nullable=False),
        sa.Column("purchase_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_selection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="DRAFT"),
        sa.Column("po_date", sa.Date(), nullable=False, server_default=sa.func.current_date()),
        sa.Column("required_date", sa.Date(), nullable=True),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("tax_amount", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("delivery_days", sa.Numeric(8, 0), nullable=False, server_default="0"),
        sa.Column("payment_terms_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["purchase_request_id"], ["purchase_requests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supplier_selection_id"], ["supplier_selections.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("po_number", name="uq_purchase_orders_po_number"),
        sa.UniqueConstraint("supplier_selection_id", name="uq_purchase_order_supplier_selection"),
    )
    op.create_index("ix_purchase_orders_po_number", "purchase_orders", ["po_number"])
    op.create_index("ix_purchase_orders_purchase_request_id", "purchase_orders", ["purchase_request_id"])
    op.create_index("ix_purchase_orders_supplier_selection_id", "purchase_orders", ["supplier_selection_id"])
    op.create_index("ix_purchase_orders_vendor_id", "purchase_orders", ["vendor_id"])
    op.create_index("ix_purchase_orders_status", "purchase_orders", ["status"])

    op.create_table(
        "purchase_order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=700), nullable=True),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("specifications", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_item_id"], ["purchase_request_items.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_purchase_order_items_purchase_order_id", "purchase_order_items", ["purchase_order_id"])
    op.create_index("ix_purchase_order_items_request_item_id", "purchase_order_items", ["request_item_id"])


def downgrade():
    op.drop_index("ix_purchase_order_items_request_item_id", table_name="purchase_order_items")
    op.drop_index("ix_purchase_order_items_purchase_order_id", table_name="purchase_order_items")
    op.drop_table("purchase_order_items")
    op.drop_index("ix_purchase_orders_status", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_vendor_id", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_supplier_selection_id", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_purchase_request_id", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_po_number", table_name="purchase_orders")
    op.drop_table("purchase_orders")
