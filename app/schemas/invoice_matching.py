import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class InvoiceMatchLine(BaseModel):
    purchase_order_item_id: uuid.UUID
    description: str
    po_quantity: Decimal
    received_quantity: Decimal
    accepted_quantity: Decimal
    invoice_quantity: Decimal
    po_unit_price: Decimal
    invoice_unit_price: Decimal
    quantity_variance: Decimal
    price_variance: Decimal
    quantity_pass: bool
    price_pass: bool
    receipt_pass: bool


class InvoiceMatchResponse(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    invoice_number: str
    purchase_order_id: uuid.UUID
    po_number: str
    supplier_name: str
    currency: str
    result: str
    po_quantity: Decimal
    received_quantity: Decimal
    accepted_quantity: Decimal
    invoice_quantity: Decimal
    quantity_variance: Decimal
    po_amount: Decimal
    invoice_amount: Decimal
    price_variance: Decimal
    price_variance_percent: Decimal
    quantity_tolerance: Decimal
    price_tolerance_percent: Decimal
    exception_reason: str | None
    line_results: list[InvoiceMatchLine]
    evaluated_by_user_id: uuid.UUID
    evaluated_at: datetime


class InvoiceMatchingQueueItem(BaseModel):
    invoice_id: uuid.UUID
    invoice_number: str
    purchase_order_id: uuid.UUID
    po_number: str
    supplier_name: str
    currency: str
    total_amount: Decimal
    invoice_date: date | None = None
    status: str
