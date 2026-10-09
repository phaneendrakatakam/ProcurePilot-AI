import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class PurchaseOrderCreate(BaseModel):
    supplier_selection_id: uuid.UUID
    payment_terms_days: int = 30
    notes: str | None = None


class PurchaseOrderItemResponse(BaseModel):
    id: uuid.UUID
    request_item_id: uuid.UUID | None
    name: str
    description: str | None
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    specifications: dict | None


class PurchaseOrderSummary(BaseModel):
    id: uuid.UUID
    po_number: str
    purchase_request_id: uuid.UUID
    request_number: str
    supplier_selection_id: uuid.UUID
    vendor_id: uuid.UUID
    supplier_code: str
    supplier_name: str
    currency: str
    status: str
    po_date: date
    required_date: date | None
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    delivery_days: int
    payment_terms_days: int
    issued_at: datetime | None
    supplier_notification_status: str
    supplier_notification_sent_at: datetime | None
    supplier_notification_error: str | None
    created_by_user_id: uuid.UUID


class PurchaseOrderDetail(PurchaseOrderSummary):
    notes: str | None
    items: list[PurchaseOrderItemResponse]
