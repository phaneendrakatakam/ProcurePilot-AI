"""repair supplier invoice tables if the invoice migration was already stamped

Revision ID: 9c6e1f4a2b70
Revises: 8b5d2f7c1a40
Create Date: 2026-09-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "9c6e1f4a2b70"
down_revision = "8b5d2f7c1a40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("supplier_invoices"):
        op.create_table(
            "supplier_invoices",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("invoice_number", sa.String(length=80), nullable=False),
            sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("invoice_date", sa.Date(), nullable=False),
            sa.Column("due_date", sa.Date(), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
            sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
            sa.Column(
                "tax_amount",
                sa.Numeric(18, 2),
                nullable=False,
                server_default="0.00",
            ),
            sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default="RECEIVED",
            ),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["vendor_id"], ["vendors.id"], ondelete="RESTRICT"
            ),
            sa.ForeignKeyConstraint(
                ["purchase_order_id"],
                ["purchase_orders.id"],
                ondelete="RESTRICT",
            ),
            sa.ForeignKeyConstraint(
                ["created_by_user_id"],
                ["users.id"],
                ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "vendor_id",
                "invoice_number",
                name="uq_supplier_invoice_vendor_number",
            ),
            sa.CheckConstraint(
                "subtotal >= 0",
                name="ck_supplier_invoice_subtotal_nonnegative",
            ),
            sa.CheckConstraint(
                "tax_amount >= 0",
                name="ck_supplier_invoice_tax_nonnegative",
            ),
            sa.CheckConstraint(
                "total_amount >= 0",
                name="ck_supplier_invoice_total_nonnegative",
            ),
        )

    inspector = sa.inspect(bind)

    if not inspector.has_table("supplier_invoice_items"):
        op.create_table(
            "supplier_invoice_items",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "purchase_order_item_id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
            ),
            sa.Column("description", sa.String(length=500), nullable=False),
            sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
            sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
            sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
            sa.ForeignKeyConstraint(
                ["invoice_id"],
                ["supplier_invoices.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["purchase_order_item_id"],
                ["purchase_order_items.id"],
                ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "invoice_id",
                "purchase_order_item_id",
                name="uq_supplier_invoice_item_po_line",
            ),
            sa.CheckConstraint(
                "quantity > 0",
                name="ck_supplier_invoice_item_quantity_positive",
            ),
            sa.CheckConstraint(
                "unit_price >= 0",
                name="ck_supplier_invoice_item_unit_price_nonnegative",
            ),
            sa.CheckConstraint(
                "line_total >= 0",
                name="ck_supplier_invoice_item_total_nonnegative",
            ),
        )

    inspector = sa.inspect(bind)
    invoice_indexes = {
        index["name"] for index in inspector.get_indexes("supplier_invoices")
    }
    for name, column in (
        ("ix_supplier_invoices_invoice_number", "invoice_number"),
        ("ix_supplier_invoices_vendor_id", "vendor_id"),
        ("ix_supplier_invoices_purchase_order_id", "purchase_order_id"),
        ("ix_supplier_invoices_status", "status"),
    ):
        if name not in invoice_indexes:
            op.create_index(name, "supplier_invoices", [column], unique=False)

    inspector = sa.inspect(bind)
    item_indexes = {
        index["name"] for index in inspector.get_indexes("supplier_invoice_items")
    }
    for name, column in (
        ("ix_supplier_invoice_items_invoice_id", "invoice_id"),
        ("ix_supplier_invoice_items_purchase_order_item_id", "purchase_order_item_id"),
    ):
        if name not in item_indexes:
            op.create_index(name, "supplier_invoice_items", [column], unique=False)


def downgrade() -> None:
    # This repair migration must not remove tables created by revision 8b5d2f7c1a40.
    # The original invoice migration owns the schema and its downgrade remains authoritative.
    pass
