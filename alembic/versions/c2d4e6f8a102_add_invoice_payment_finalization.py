"""add finance payment finalization fields to supplier invoices

Revision ID: c2d4e6f8a102
Revises: b1c4d6e8f902
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c2d4e6f8a102"
down_revision = "b1c4d6e8f902"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("supplier_invoices", sa.Column("payment_reference", sa.String(length=80), nullable=True))
    op.add_column("supplier_invoices", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("supplier_invoices", sa.Column("paid_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_unique_constraint("uq_supplier_invoice_payment_reference", "supplier_invoices", ["payment_reference"])
    op.create_index("ix_supplier_invoices_payment_reference", "supplier_invoices", ["payment_reference"], unique=False)
    op.create_foreign_key("fk_supplier_invoices_paid_by_user", "supplier_invoices", "users", ["paid_by_user_id"], ["id"], ondelete="RESTRICT")

def downgrade() -> None:
    op.drop_constraint("fk_supplier_invoices_paid_by_user", "supplier_invoices", type_="foreignkey")
    op.drop_index("ix_supplier_invoices_payment_reference", table_name="supplier_invoices")
    op.drop_constraint("uq_supplier_invoice_payment_reference", "supplier_invoices", type_="unique")
    op.drop_column("supplier_invoices", "paid_by_user_id")
    op.drop_column("supplier_invoices", "paid_at")
    op.drop_column("supplier_invoices", "payment_reference")
