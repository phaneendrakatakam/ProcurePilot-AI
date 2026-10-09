from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class GoodsReceipt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A receiving document for goods delivered against an issued purchase order."""

    __tablename__ = "goods_receipts"
    __table_args__ = (
        UniqueConstraint("receipt_number", name="uq_goods_receipt_number"),
    )

    receipt_number: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    received_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    receipt_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="DRAFT", index=True
    )
    delivery_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    purchase_order = relationship("PurchaseOrder")
    received_by = relationship("User")
    items: Mapped[list["GoodsReceiptItem"]] = relationship(
        back_populates="receipt",
        cascade="all, delete-orphan",
        order_by="GoodsReceiptItem.created_at",
    )


class GoodsReceiptItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Quantity evidence captured for one purchase-order line."""

    __tablename__ = "goods_receipt_items"
    __table_args__ = (
        UniqueConstraint(
            "goods_receipt_id",
            "purchase_order_item_id",
            name="uq_goods_receipt_item_line",
        ),
        CheckConstraint(
            "received_quantity > 0",
            name="ck_goods_receipt_received_positive",
        ),
        CheckConstraint(
            "accepted_quantity >= 0 AND rejected_quantity >= 0",
            name="ck_goods_receipt_quantities_nonnegative",
        ),
        CheckConstraint(
            "accepted_quantity + rejected_quantity = received_quantity",
            name="ck_goods_receipt_quantity_split",
        ),
    )

    goods_receipt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("goods_receipts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    purchase_order_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_order_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    received_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    accepted_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    rejected_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    receipt = relationship("GoodsReceipt", back_populates="items")
    purchase_order_item = relationship("PurchaseOrderItem")
