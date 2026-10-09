"""add supplier quotation capture

Revision ID: 8c4e1a7d2b90
Revises: 7b2c9d4e1f60
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "8c4e1a7d2b90"
down_revision = "7b2c9d4e1f60"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "supplier_quotations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("rfq_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rfq_supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("quoted_quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("delivery_days", sa.Numeric(8, 0), nullable=False, server_default="0"),
        sa.Column("valid_until", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("recorded_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["rfq_id"], ["rfqs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rfq_supplier_id"], ["rfq_suppliers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("rfq_supplier_id", name="uq_supplier_quotation_rfq_supplier"),
    )
    op.create_index("ix_supplier_quotations_rfq_id", "supplier_quotations", ["rfq_id"])
    op.create_index("ix_supplier_quotations_rfq_supplier_id", "supplier_quotations", ["rfq_supplier_id"])
    op.create_index("ix_supplier_quotations_status", "supplier_quotations", ["status"])


def downgrade():
    op.drop_index("ix_supplier_quotations_status", table_name="supplier_quotations")
    op.drop_index("ix_supplier_quotations_rfq_supplier_id", table_name="supplier_quotations")
    op.drop_index("ix_supplier_quotations_rfq_id", table_name="supplier_quotations")
    op.drop_table("supplier_quotations")
