from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SupplierInvoiceMatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted 3-way match evaluation for a supplier invoice."""

    __tablename__ = "supplier_invoice_matches"
    __table_args__ = (
        UniqueConstraint("invoice_id", name="uq_supplier_invoice_match_invoice"),
    )

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    result: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    po_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    accepted_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    invoice_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity_variance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    po_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    invoice_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    price_variance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    price_variance_percent: Mapped[Decimal] = mapped_column(Numeric(9, 4), nullable=False)
    quantity_tolerance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    price_tolerance_percent: Mapped[Decimal] = mapped_column(Numeric(9, 4), nullable=False)
    exception_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    line_results: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    evaluated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    invoice = relationship("SupplierInvoice")
    purchase_order = relationship("PurchaseOrder")
    evaluated_by = relationship("User")
