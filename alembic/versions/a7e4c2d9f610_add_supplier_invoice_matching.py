"""add persisted supplier invoice 3-way matching evaluations

Revision ID: a7e4c2d9f610
Revises: 9c6e1f4a2b70
Create Date: 2026-09-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a7e4c2d9f610"
down_revision = "9c6e1f4a2b70"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supplier_invoice_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("result", sa.String(length=24), nullable=False),
        sa.Column("po_quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("received_quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("accepted_quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("invoice_quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("quantity_variance", sa.Numeric(12, 2), nullable=False),
        sa.Column("po_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("invoice_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("price_variance", sa.Numeric(18, 2), nullable=False),
        sa.Column("price_variance_percent", sa.Numeric(9, 4), nullable=False),
        sa.Column("quantity_tolerance", sa.Numeric(12, 2), nullable=False),
        sa.Column("price_tolerance_percent", sa.Numeric(9, 4), nullable=False),
        sa.Column("exception_reason", sa.String(length=1000), nullable=True),
        sa.Column("line_results", sa.JSON(), nullable=True),
        sa.Column("evaluated_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["invoice_id"], ["supplier_invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evaluated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_id", name="uq_supplier_invoice_match_invoice"),
    )
    op.create_index("ix_supplier_invoice_matches_invoice_id", "supplier_invoice_matches", ["invoice_id"], unique=False)
    op.create_index("ix_supplier_invoice_matches_purchase_order_id", "supplier_invoice_matches", ["purchase_order_id"], unique=False)
    op.create_index("ix_supplier_invoice_matches_result", "supplier_invoice_matches", ["result"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_supplier_invoice_matches_result", table_name="supplier_invoice_matches")
    op.drop_index("ix_supplier_invoice_matches_purchase_order_id", table_name="supplier_invoice_matches")
    op.drop_index("ix_supplier_invoice_matches_invoice_id", table_name="supplier_invoice_matches")
    op.drop_table("supplier_invoice_matches")
