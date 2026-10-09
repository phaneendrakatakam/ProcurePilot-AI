from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SupplierInvoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Supplier invoice captured for AP processing against a purchase order."""

    __tablename__ = "supplier_invoices"
    __table_args__ = (
        UniqueConstraint("vendor_id", "invoice_number", name="uq_supplier_invoice_vendor_number"),
        CheckConstraint("subtotal >= 0", name="ck_supplier_invoice_subtotal_nonnegative"),
        CheckConstraint("tax_amount >= 0", name="ck_supplier_invoice_tax_nonnegative"),
        CheckConstraint("total_amount >= 0", name="ck_supplier_invoice_total_nonnegative"),
    )

    invoice_number: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="RECEIVED", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(80), nullable=True, unique=True, index=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    paid_by = relationship("User", foreign_keys=[paid_by_user_id])

    vendor = relationship("Vendor")
    purchase_order = relationship("PurchaseOrder")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    items: Mapped[list["SupplierInvoiceItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", order_by="SupplierInvoiceItem.created_at"
    )


class SupplierInvoiceItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Invoice line captured against a specific PO line for future 3-way matching."""

    __tablename__ = "supplier_invoice_items"
    __table_args__ = (
        UniqueConstraint("invoice_id", "purchase_order_item_id", name="uq_supplier_invoice_item_po_line"),
        CheckConstraint("quantity > 0", name="ck_supplier_invoice_item_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_supplier_invoice_item_unit_price_nonnegative"),
        CheckConstraint("line_total >= 0", name="ck_supplier_invoice_item_total_nonnegative"),
    )

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purchase_order_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_order_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    invoice = relationship("SupplierInvoice", back_populates="items")
    purchase_order_item = relationship("PurchaseOrderItem")
