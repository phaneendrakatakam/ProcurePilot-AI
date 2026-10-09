"""add purchase request approval workflow

Revision ID: 2f7c1a9e6b40
Revises: 9d5e7f1b3c20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "2f7c1a9e6b40"
down_revision = "9d5e7f1b3c20"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "purchase_request_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("purchase_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approver_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approver_role", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("decision_comment", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["purchase_request_id"],
            ["purchase_requests.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["approver_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "purchase_request_id",
            "sequence",
            name="uq_purchase_request_approval_sequence",
        ),
    )
    op.create_index(
        "ix_purchase_request_approvals_purchase_request_id",
        "purchase_request_approvals",
        ["purchase_request_id"],
    )
    op.create_index(
        "ix_purchase_request_approvals_approver_user_id",
        "purchase_request_approvals",
        ["approver_user_id"],
    )
    op.create_index(
        "ix_purchase_request_approvals_status",
        "purchase_request_approvals",
        ["status"],
    )


def downgrade():
    op.drop_index(
        "ix_purchase_request_approvals_status",
        table_name="purchase_request_approvals",
    )
    op.drop_index(
        "ix_purchase_request_approvals_approver_user_id",
        table_name="purchase_request_approvals",
    )
    op.drop_index(
        "ix_purchase_request_approvals_purchase_request_id",
        table_name="purchase_request_approvals",
    )
    op.drop_table("purchase_request_approvals")
