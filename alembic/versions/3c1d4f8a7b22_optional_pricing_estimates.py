"""make purchase pricing estimates optional

Revision ID: 3c1d4f8a7b22
Revises: 9a4f2d8c1b77
Create Date: 2026-09-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "3c1d4f8a7b22"
down_revision: Union[str, Sequence[str], None] = "9a4f2d8c1b77"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "purchase_requests",
        sa.Column("estimated_budget", sa.Numeric(18, 2), nullable=True),
    )
    op.alter_column(
        "purchase_requests",
        "currency",
        existing_type=sa.String(length=3),
        nullable=True,
    )
    op.alter_column(
        "purchase_requests",
        "estimated_total",
        existing_type=sa.Numeric(precision=18, scale=2),
        nullable=True,
        server_default=None,
    )

    op.alter_column(
        "purchase_request_items",
        "unit_price",
        existing_type=sa.Numeric(precision=18, scale=2),
        nullable=True,
    )
    op.alter_column(
        "purchase_request_items",
        "line_total",
        existing_type=sa.Numeric(precision=18, scale=2),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "purchase_request_items",
        "line_total",
        existing_type=sa.Numeric(precision=18, scale=2),
        nullable=False,
    )
    op.alter_column(
        "purchase_request_items",
        "unit_price",
        existing_type=sa.Numeric(precision=18, scale=2),
        nullable=False,
    )
    op.alter_column(
        "purchase_requests",
        "estimated_total",
        existing_type=sa.Numeric(precision=18, scale=2),
        nullable=False,
        server_default="0",
    )
    op.alter_column(
        "purchase_requests",
        "currency",
        existing_type=sa.String(length=3),
        nullable=False,
        server_default="INR",
    )
    op.drop_column("purchase_requests", "estimated_budget")
