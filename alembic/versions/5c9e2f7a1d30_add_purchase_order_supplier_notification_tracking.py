"""add purchase order supplier notification tracking

Revision ID: 5c9e2f7a1d30
Revises: 4b7c2d9e1f50
"""
from alembic import op
import sqlalchemy as sa

revision = "5c9e2f7a1d30"
down_revision = "4b7c2d9e1f50"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("purchase_orders", sa.Column("supplier_notification_status", sa.String(length=24), nullable=False, server_default="NOT_SENT"))
    op.add_column("purchase_orders", sa.Column("supplier_notification_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("purchase_orders", sa.Column("supplier_notification_error", sa.String(length=500), nullable=True))
    op.create_index("ix_purchase_orders_supplier_notification_status", "purchase_orders", ["supplier_notification_status"])


def downgrade():
    op.drop_index("ix_purchase_orders_supplier_notification_status", table_name="purchase_orders")
    op.drop_column("purchase_orders", "supplier_notification_error")
    op.drop_column("purchase_orders", "supplier_notification_sent_at")
    op.drop_column("purchase_orders", "supplier_notification_status")
