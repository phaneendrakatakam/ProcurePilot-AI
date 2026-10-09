"""add supplier email quotation portal

Revision ID: 3a8f6e2b1c40
Revises: 2f7c1a9e6b40
"""
from alembic import op
import sqlalchemy as sa

revision = "3a8f6e2b1c40"
down_revision = "2f7c1a9e6b40"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("rfq_suppliers", sa.Column("response_token_hash", sa.String(length=64), nullable=True))
    op.add_column("rfq_suppliers", sa.Column("response_token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rfq_suppliers", sa.Column("response_submitted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_rfq_suppliers_response_token_hash", "rfq_suppliers", ["response_token_hash"], unique=True)
    op.add_column("supplier_quotations", sa.Column("submission_source", sa.String(length=24), nullable=False, server_default="INTERNAL"))
    op.alter_column("supplier_quotations", "recorded_by_user_id", existing_type=sa.UUID(), nullable=True)


def downgrade():
    op.alter_column("supplier_quotations", "recorded_by_user_id", existing_type=sa.UUID(), nullable=False)
    op.drop_column("supplier_quotations", "submission_source")
    op.drop_index("ix_rfq_suppliers_response_token_hash", table_name="rfq_suppliers")
    op.drop_column("rfq_suppliers", "response_submitted_at")
    op.drop_column("rfq_suppliers", "response_token_expires_at")
    op.drop_column("rfq_suppliers", "response_token_hash")
