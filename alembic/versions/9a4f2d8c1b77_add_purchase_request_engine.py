"""add purchase request engine

Revision ID: 9a4f2d8c1b77
Revises: 75d655a8e857
Create Date: 2026-09-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "9a4f2d8c1b77"
down_revision: Union[str, Sequence[str], None] = "75d655a8e857"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "purchase_requests",
        sa.Column("request_number", sa.String(length=40), nullable=False),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("required_date", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
        sa.Column("estimated_total", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="DRAFT"),
        sa.Column("budget_check_status", sa.String(length=32), nullable=False, server_default="NOT_CHECKED"),
        sa.Column("budget_check_message", sa.String(length=700), nullable=True),
        sa.Column("policy_check_status", sa.String(length=32), nullable=False, server_default="NOT_CHECKED"),
        sa.Column("policy_check_message", sa.String(length=700), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("ai_structured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_number"),
    )
    op.create_index("ix_purchase_requests_requester_id", "purchase_requests", ["requester_id"])
    op.create_index("ix_purchase_requests_department_id", "purchase_requests", ["department_id"])
    op.create_index("ix_purchase_requests_category", "purchase_requests", ["category"])
    op.create_index("ix_purchase_requests_status", "purchase_requests", ["status"])

    op.create_table(
        "purchase_request_items",
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=700), nullable=True),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("specifications", sa.JSON(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("quantity > 0", name="ck_purchase_request_item_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_purchase_request_item_unit_price_nonnegative"),
        sa.ForeignKeyConstraint(["request_id"], ["purchase_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_request_items_request_id", "purchase_request_items", ["request_id"])

    op.create_table(
        "clarification_tasks",
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field_name", sa.String(length=120), nullable=False),
        sa.Column("question", sa.String(length=700), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN"),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("created_by_actor_type", sa.String(length=20), nullable=False, server_default="SYSTEM"),
        sa.Column("answered_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["answered_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["request_id"], ["purchase_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clarification_tasks_request_id", "clarification_tasks", ["request_id"])
    op.create_index("ix_clarification_tasks_status", "clarification_tasks", ["status"])

    op.create_table(
        "request_events",
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_type", sa.String(length=20), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("from_status", sa.String(length=40), nullable=True),
        sa.Column("to_status", sa.String(length=40), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["request_id"], ["purchase_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_request_events_request_id", "request_events", ["request_id"])
    op.create_index("ix_request_events_actor_type", "request_events", ["actor_type"])
    op.create_index("ix_request_events_event_type", "request_events", ["event_type"])
    op.create_index("ix_request_events_created_at", "request_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_request_events_created_at", table_name="request_events")
    op.drop_index("ix_request_events_event_type", table_name="request_events")
    op.drop_index("ix_request_events_actor_type", table_name="request_events")
    op.drop_index("ix_request_events_request_id", table_name="request_events")
    op.drop_table("request_events")
    op.drop_index("ix_clarification_tasks_status", table_name="clarification_tasks")
    op.drop_index("ix_clarification_tasks_request_id", table_name="clarification_tasks")
    op.drop_table("clarification_tasks")
    op.drop_index("ix_purchase_request_items_request_id", table_name="purchase_request_items")
    op.drop_table("purchase_request_items")
    op.drop_index("ix_purchase_requests_status", table_name="purchase_requests")
    op.drop_index("ix_purchase_requests_category", table_name="purchase_requests")
    op.drop_index("ix_purchase_requests_department_id", table_name="purchase_requests")
    op.drop_index("ix_purchase_requests_requester_id", table_name="purchase_requests")
    op.drop_table("purchase_requests")
