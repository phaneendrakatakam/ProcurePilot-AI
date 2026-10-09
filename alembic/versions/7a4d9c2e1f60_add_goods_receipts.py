"""add goods receipt receiving documents

Revision ID: 7a4d9c2e1f60
Revises: 5c9e2f7a1d30
Create Date: 2026-09-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "7a4d9c2e1f60"
down_revision = "5c9e2f7a1d30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "goods_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("receipt_number", sa.String(length=40), nullable=False),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("received_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receipt_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="DRAFT"),
        sa.Column("delivery_reference", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["received_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("receipt_number", name="uq_goods_receipt_number"),
    )
    op.create_index("ix_goods_receipts_receipt_number", "goods_receipts", ["receipt_number"], unique=False)
    op.create_index("ix_goods_receipts_purchase_order_id", "goods_receipts", ["purchase_order_id"], unique=False)
    op.create_index("ix_goods_receipts_received_by_user_id", "goods_receipts", ["received_by_user_id"], unique=False)
    op.create_index("ix_goods_receipts_status", "goods_receipts", ["status"], unique=False)

    op.create_table(
        "goods_receipt_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("goods_receipt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_order_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("received_quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("accepted_quantity", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("rejected_quantity", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["goods_receipt_id"], ["goods_receipts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["purchase_order_item_id"], ["purchase_order_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("goods_receipt_id", "purchase_order_item_id", name="uq_goods_receipt_item_line"),
        sa.CheckConstraint("received_quantity > 0", name="ck_goods_receipt_received_positive"),
        sa.CheckConstraint(
            "accepted_quantity >= 0 AND rejected_quantity >= 0",
            name="ck_goods_receipt_quantities_nonnegative",
        ),
        sa.CheckConstraint(
            "accepted_quantity + rejected_quantity = received_quantity",
            name="ck_goods_receipt_quantity_split",
        ),
    )
    op.create_index("ix_goods_receipt_items_goods_receipt_id", "goods_receipt_items", ["goods_receipt_id"], unique=False)
    op.create_index("ix_goods_receipt_items_purchase_order_item_id", "goods_receipt_items", ["purchase_order_item_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_goods_receipt_items_purchase_order_item_id", table_name="goods_receipt_items")
    op.drop_index("ix_goods_receipt_items_goods_receipt_id", table_name="goods_receipt_items")
    op.drop_table("goods_receipt_items")
    op.drop_index("ix_goods_receipts_status", table_name="goods_receipts")
    op.drop_index("ix_goods_receipts_received_by_user_id", table_name="goods_receipts")
    op.drop_index("ix_goods_receipts_purchase_order_id", table_name="goods_receipts")
    op.drop_index("ix_goods_receipts_receipt_number", table_name="goods_receipts")
    op.drop_table("goods_receipts")
