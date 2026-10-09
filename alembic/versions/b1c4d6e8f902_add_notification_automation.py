"""add notification automation notifications

Revision ID: b1c4d6e8f902
Revises: a7e4c2d9f610
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b1c4d6e8f902"
down_revision = "a7e4c2d9f610"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("notification_type", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=24), nullable=False, server_default="EMAIL"),
        sa.Column("subject", sa.String(length=240), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=False),
        sa.Column("dedupe_key", sa.String(length=240), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="PENDING"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key", name="uq_notifications_dedupe_key"),
    )
    op.create_index("ix_notifications_recipient_user_id", "notifications", ["recipient_user_id"], unique=False)
    op.create_index("ix_notifications_notification_type", "notifications", ["notification_type"], unique=False)
    op.create_index("ix_notifications_entity_type", "notifications", ["entity_type"], unique=False)
    op.create_index("ix_notifications_entity_id", "notifications", ["entity_id"], unique=False)
    op.create_index("ix_notifications_dedupe_key", "notifications", ["dedupe_key"], unique=False)
    op.create_index("ix_notifications_status", "notifications", ["status"], unique=False)


def downgrade():
    op.drop_index("ix_notifications_status", table_name="notifications")
    op.drop_index("ix_notifications_dedupe_key", table_name="notifications")
    op.drop_index("ix_notifications_entity_id", table_name="notifications")
    op.drop_index("ix_notifications_entity_type", table_name="notifications")
    op.drop_index("ix_notifications_notification_type", table_name="notifications")
    op.drop_index("ix_notifications_recipient_user_id", table_name="notifications")
    op.drop_table("notifications")
