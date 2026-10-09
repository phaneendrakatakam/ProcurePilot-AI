from __future__ import annotations
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PurchaseRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "purchase_requests"

    request_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True, default="INR")
    estimated_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    estimated_budget: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT", index=True)
    budget_check_status: Mapped[str] = mapped_column(String(32), nullable=False, default="NOT_CHECKED")
    budget_check_message: Mapped[str | None] = mapped_column(String(700), nullable=True)
    policy_check_status: Mapped[str] = mapped_column(String(32), nullable=False, default="NOT_CHECKED")
    policy_check_message: Mapped[str | None] = mapped_column(String(700), nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_structured: Mapped[bool] = mapped_column(nullable=False, default=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    requester = relationship("User")
    department = relationship("Department")
    items: Mapped[list["PurchaseRequestItem"]] = relationship(
        back_populates="request", cascade="all, delete-orphan", order_by="PurchaseRequestItem.created_at"
    )
    clarifications: Mapped[list["ClarificationTask"]] = relationship(
        back_populates="request", cascade="all, delete-orphan", order_by="ClarificationTask.created_at"
    )
    events: Mapped[list["RequestEvent"]] = relationship(
        back_populates="request", cascade="all, delete-orphan", order_by="RequestEvent.created_at"
    )
    approvals: Mapped[list["PurchaseRequestApproval"]] = relationship(
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="PurchaseRequestApproval.sequence",
    )


class PurchaseRequestItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "purchase_request_items"

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(700), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    line_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    specifications: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    request: Mapped[PurchaseRequest] = relationship(back_populates="items")


class ClarificationTask(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "clarification_tasks"

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(120), nullable=False)
    question: Mapped[str] = mapped_column(String(700), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN", index=True)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_actor_type: Mapped[str] = mapped_column(String(20), nullable=False, default="SYSTEM")
    answered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    request: Mapped[PurchaseRequest] = relationship(back_populates="clarifications")


class RequestEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "request_events"

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    request: Mapped[PurchaseRequest] = relationship(back_populates="events")


class RFQ(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rfqs"

    rfq_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_requests.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT", index=True)
    response_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    request: Mapped[PurchaseRequest] = relationship()
    created_by = relationship("User")
    suppliers: Mapped[list[RFQSupplier]] = relationship(
        back_populates="rfq", cascade="all, delete-orphan", order_by="RFQSupplier.created_at"
    )


class RFQSupplier(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rfq_suppliers"

    rfq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="INVITED")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    response_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    rfq: Mapped[RFQ] = relationship(back_populates="suppliers")
    vendor = relationship("Vendor")
    quotation: Mapped["SupplierQuotation | None"] = relationship(back_populates="rfq_supplier", uselist=False)


class SupplierQuotation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supplier_quotations"
    __table_args__ = (
        UniqueConstraint("rfq_supplier_id", name="uq_supplier_quotation_rfq_supplier"),
    )

    rfq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rfq_supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rfq_suppliers.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    quoted_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    delivery_days: Mapped[int] = mapped_column(Numeric(8, 0), nullable=False, default=0)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="RECEIVED", index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    recorded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    submission_source: Mapped[str] = mapped_column(String(24), nullable=False, default="INTERNAL")

    rfq = relationship("RFQ")
    rfq_supplier = relationship("RFQSupplier", back_populates="quotation")
    recorded_by = relationship("User")
    items: Mapped[list["SupplierQuotationItem"]] = relationship(
        back_populates="quotation", cascade="all, delete-orphan", order_by="SupplierQuotationItem.created_at"
    )


class SupplierQuotationItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A supplier price for one original requested item; historical package quotations have no rows."""
    __tablename__ = "supplier_quotation_items"
    __table_args__ = (UniqueConstraint("supplier_quotation_id", "request_item_id", name="uq_quotation_item_request"),)
    supplier_quotation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_quotations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    request_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_request_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    quotation = relationship("SupplierQuotation", back_populates="items")
    request_item = relationship("PurchaseRequestItem")


class SupplierSelection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supplier_selections"
    __table_args__ = (
        UniqueConstraint("rfq_id", name="uq_supplier_selection_rfq"),
        UniqueConstraint("rfq_supplier_id", name="uq_supplier_selection_rfq_supplier"),
    )

    rfq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rfq_supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rfq_suppliers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quotation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_quotations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    selected_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    rfq = relationship("RFQ")
    rfq_supplier = relationship("RFQSupplier")
    quotation = relationship("SupplierQuotation")
    selected_by = relationship("User")

class PurchaseRequestApproval(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One ordered human approval step for a purchase request."""

    __tablename__ = "purchase_request_approvals"
    __table_args__ = (
        UniqueConstraint(
            "purchase_request_id",
            "sequence",
            name="uq_purchase_request_approval_sequence",
        ),
    )

    purchase_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approver_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    approver_role: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",
        index=True,
    )
    decision_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    request = relationship("PurchaseRequest", back_populates="approvals")
    approver = relationship("User")

class PurchaseOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Purchasing document generated from an approved supplier selection."""

    __tablename__ = "purchase_orders"
    __table_args__ = (
        UniqueConstraint(
            "supplier_selection_id",
            name="uq_purchase_order_supplier_selection",
        ),
    )

    po_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    purchase_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_requests.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    supplier_selection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_selections.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT", index=True)
    po_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    required_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    delivery_days: Mapped[int] = mapped_column(Numeric(8, 0), nullable=False, default=0)
    payment_terms_days: Mapped[int] = mapped_column(nullable=False, default=30)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supplier_notification_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="NOT_SENT", index=True
    )
    supplier_notification_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    supplier_notification_error: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    request = relationship("PurchaseRequest")
    supplier_selection = relationship("SupplierSelection")
    vendor = relationship("Vendor")
    created_by = relationship("User")
    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        back_populates="purchase_order",
        cascade="all, delete-orphan",
        order_by="PurchaseOrderItem.created_at",
    )


class PurchaseOrderItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Immutable purchasing snapshot of a requested line used by the PO."""

    __tablename__ = "purchase_order_items"

    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    request_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_request_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(700), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    specifications: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    request_item = relationship("PurchaseRequestItem")
