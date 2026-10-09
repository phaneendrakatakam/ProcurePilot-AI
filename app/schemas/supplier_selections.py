import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class SupplierSelectionCreate(BaseModel):
    rfq_id: uuid.UUID
    rfq_supplier_id: uuid.UUID
    rationale: str = Field(min_length=10, max_length=2000)


class SupplierSelectionSummary(BaseModel):
    id: uuid.UUID
    rfq_id: uuid.UUID
    rfq_number: str
    request_id: uuid.UUID
    request_number: str
    request_title: str
    rfq_supplier_id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_code: str
    supplier_name: str
    quotation_id: uuid.UUID
    currency: str
    quoted_quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    delivery_days: int
    valid_until: date
    rationale: str
    selected_at: datetime
    selected_by_user_id: uuid.UUID


class SupplierSelectionDetail(SupplierSelectionSummary):
    pass
