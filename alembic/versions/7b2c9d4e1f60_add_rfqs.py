"""add rfq sourcing events

Revision ID: 7b2c9d4e1f60
Revises: 6e8f2a1c4d90
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "7b2c9d4e1f60"
down_revision = "6e8f2a1c4d90"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "rfqs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("rfq_number", sa.String(length=40), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("response_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["request_id"], ["purchase_requests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("rfq_number"),
    )
    op.create_index("ix_rfqs_rfq_number", "rfqs", ["rfq_number"], unique=True)
    op.create_index("ix_rfqs_request_id", "rfqs", ["request_id"])
    op.create_index("ix_rfqs_status", "rfqs", ["status"])
    op.create_table(
        "rfq_suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("rfq_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["rfq_id"], ["rfqs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("rfq_id", "vendor_id", name="uq_rfq_supplier"),
    )
    op.create_index("ix_rfq_suppliers_rfq_id", "rfq_suppliers", ["rfq_id"])
    op.create_index("ix_rfq_suppliers_vendor_id", "rfq_suppliers", ["vendor_id"])

def downgrade():
    op.drop_index("ix_rfq_suppliers_vendor_id", table_name="rfq_suppliers")
    op.drop_index("ix_rfq_suppliers_rfq_id", table_name="rfq_suppliers")
    op.drop_table("rfq_suppliers")
    op.drop_index("ix_rfqs_status", table_name="rfqs")
    op.drop_index("ix_rfqs_request_id", table_name="rfqs")
    op.drop_index("ix_rfqs_rfq_number", table_name="rfqs")
    op.drop_table("rfqs")
