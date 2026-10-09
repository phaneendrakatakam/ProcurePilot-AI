"""Itemized supplier quotations; existing quotations stay intact.

Revision ID: d94e0b62a371
Revises: c2d4e6f8a102
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d94e0b62a371"
down_revision = "c2d4e6f8a102"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "supplier_quotation_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("supplier_quotation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("supplier_quotations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchase_request_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("supplier_quotation_id", "request_item_id", name="uq_quotation_item_request"),
        sa.CheckConstraint("quantity > 0", name="ck_quotation_item_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_quotation_item_price_nonnegative"),
    )
    op.create_index("ix_supplier_quotation_items_supplier_quotation_id", "supplier_quotation_items", ["supplier_quotation_id"])
    op.create_index("ix_supplier_quotation_items_request_item_id", "supplier_quotation_items", ["request_item_id"])

def downgrade():
    op.drop_index("ix_supplier_quotation_items_request_item_id", table_name="supplier_quotation_items")
    op.drop_index("ix_supplier_quotation_items_supplier_quotation_id", table_name="supplier_quotation_items")
    op.drop_table("supplier_quotation_items")
