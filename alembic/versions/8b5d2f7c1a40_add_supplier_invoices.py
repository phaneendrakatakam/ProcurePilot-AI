"""add supplier invoices for AP

Revision ID: 8b5d2f7c1a40
Revises: 7a4d9c2e1f60
Create Date: 2026-09-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "8b5d2f7c1a40"
down_revision = "7a4d9c2e1f60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supplier_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("invoice_number", sa.String(length=80), nullable=False),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="RECEIVED"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vendor_id", "invoice_number", name="uq_supplier_invoice_vendor_number"),
        sa.CheckConstraint("subtotal >= 0", name="ck_supplier_invoice_subtotal_nonnegative"),
        sa.CheckConstraint("tax_amount >= 0", name="ck_supplier_invoice_tax_nonnegative"),
        sa.CheckConstraint("total_amount >= 0", name="ck_supplier_invoice_total_nonnegative"),
    )
    op.create_index("ix_supplier_invoices_invoice_number", "supplier_invoices", ["invoice_number"])
    op.create_index("ix_supplier_invoices_vendor_id", "supplier_invoices", ["vendor_id"])
    op.create_index("ix_supplier_invoices_purchase_order_id", "supplier_invoices", ["purchase_order_id"])
    op.create_index("ix_supplier_invoices_status", "supplier_invoices", ["status"])

    op.create_table(
        "supplier_invoice_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_order_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["supplier_invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["purchase_order_item_id"], ["purchase_order_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_id", "purchase_order_item_id", name="uq_supplier_invoice_item_po_line"),
        sa.CheckConstraint("quantity > 0", name="ck_supplier_invoice_item_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_supplier_invoice_item_unit_price_nonnegative"),
        sa.CheckConstraint("line_total >= 0", name="ck_supplier_invoice_item_total_nonnegative"),
    )
    op.create_index("ix_supplier_invoice_items_invoice_id", "supplier_invoice_items", ["invoice_id"])
    op.create_index("ix_supplier_invoice_items_purchase_order_item_id", "supplier_invoice_items", ["purchase_order_item_id"])


def downgrade() -> None:
    op.drop_index("ix_supplier_invoice_items_purchase_order_item_id", table_name="supplier_invoice_items")
    op.drop_index("ix_supplier_invoice_items_invoice_id", table_name="supplier_invoice_items")
    op.drop_table("supplier_invoice_items")
    op.drop_index("ix_supplier_invoices_status", table_name="supplier_invoices")
    op.drop_index("ix_supplier_invoices_purchase_order_id", table_name="supplier_invoices")
    op.drop_index("ix_supplier_invoices_vendor_id", table_name="supplier_invoices")
    op.drop_index("ix_supplier_invoices_invoice_number", table_name="supplier_invoices")
    op.drop_table("supplier_invoices")
