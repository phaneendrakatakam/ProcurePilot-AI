"""add supplier selection

Revision ID: 9d5e7f1b3c20
Revises: 8c4e1a7d2b90
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "9d5e7f1b3c20"
down_revision = "8c4e1a7d2b90"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "supplier_selections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("rfq_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rfq_supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quotation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("selected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("selected_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["rfq_id"], ["rfqs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rfq_supplier_id"], ["rfq_suppliers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["quotation_id"], ["supplier_quotations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["selected_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("rfq_id", name="uq_supplier_selection_rfq"),
        sa.UniqueConstraint("rfq_supplier_id", name="uq_supplier_selection_rfq_supplier"),
    )
    op.create_index("ix_supplier_selections_rfq_id", "supplier_selections", ["rfq_id"])
    op.create_index("ix_supplier_selections_rfq_supplier_id", "supplier_selections", ["rfq_supplier_id"])
    op.create_index("ix_supplier_selections_quotation_id", "supplier_selections", ["quotation_id"])


def downgrade():
    op.drop_index("ix_supplier_selections_quotation_id", table_name="supplier_selections")
    op.drop_index("ix_supplier_selections_rfq_supplier_id", table_name="supplier_selections")
    op.drop_index("ix_supplier_selections_rfq_id", table_name="supplier_selections")
    op.drop_table("supplier_selections")
