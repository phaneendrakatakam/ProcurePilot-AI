"""expand vendor master for supplier sourcing"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "6e8f2a1c4d90"
down_revision: Union[str, Sequence[str], None] = "3c1d4f8a7b22"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vendors", sa.Column("contact_person", sa.String(length=160), nullable=True))
    op.add_column("vendors", sa.Column("phone", sa.String(length=40), nullable=True))
    op.add_column("vendors", sa.Column("address", sa.String(length=500), nullable=True))
    op.add_column("vendors", sa.Column("capabilities", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("vendors", "capabilities")
    op.drop_column("vendors", "address")
    op.drop_column("vendors", "phone")
    op.drop_column("vendors", "contact_person")
