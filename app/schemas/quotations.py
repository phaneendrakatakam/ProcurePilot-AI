import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class QuotationLineInput(BaseModel):
    request_item_id: uuid.UUID
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    unit_price: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class QuotationLineResponse(QuotationLineInput):
    line_total: Decimal
    item_name: str


class QuotationCreate(BaseModel):
    rfq_id: uuid.UUID
    rfq_supplier_id: uuid.UUID
    currency: str = Field(default="INR", min_length=3, max_length=3)
    quoted_quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    unit_price: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=18, decimal_places=2)
    delivery_days: int = Field(default=0, ge=0, le=3650)
    valid_until: date
    notes: str | None = Field(default=None, max_length=2000)
    items: list[QuotationLineInput] | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()


class QuotationSummary(BaseModel):
    items: list[QuotationLineResponse] = Field(default_factory=list)
    id: uuid.UUID
    rfq_id: uuid.UUID
    rfq_number: str
    request_number: str
    request_title: str
    request_status: str = "UNKNOWN"
    rfq_supplier_id: uuid.UUID
    vendor_id: uuid.UUID
    vendor_code: str
    vendor_name: str
    currency: str
    quoted_quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    delivery_days: int
    valid_until: date
    status: str
    received_at: datetime
    notes: str | None
    created_at: datetime
    updated_at: datetime


class QuotationDetail(QuotationSummary):
    recorded_by_user_id: uuid.UUID | None


class PendingQuotationTarget(BaseModel):
    rfq_supplier_id: uuid.UUID
    rfq_id: uuid.UUID
    rfq_number: str
    request_number: str
    request_title: str
    request_status: str = "UNKNOWN"
    supplier_id: uuid.UUID
    supplier_code: str
    supplier_name: str
    supplier_email: str
    currency: str
    item_name: str
    quantity: Decimal
    response_deadline: datetime


class QuotationComparisonRow(BaseModel):
    rfq_supplier_id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_code: str
    supplier_name: str
    supplier_email: str
    invitation_status: str
    quotation_id: uuid.UUID | None
    quotation_status: str | None
    currency: str
    quoted_quantity: Decimal | None
    unit_price: Decimal | None
    subtotal: Decimal | None
    tax_amount: Decimal | None
    total_amount: Decimal | None
    delivery_days: int | None
    valid_until: date | None
    received_at: datetime | None
    notes: str | None
    items: list[QuotationLineResponse] = Field(default_factory=list)


class QuotationComparison(BaseModel):
    rfq_id: uuid.UUID
    rfq_number: str
    request_id: uuid.UUID
    request_number: str
    request_title: str
    request_status: str = "UNKNOWN"
    request_category: str | None
    request_currency: str
    response_deadline: datetime
    invited_supplier_count: int
    received_quotation_count: int
    pending_response_count: int
    rows: list[QuotationComparisonRow]


class SupplierQuotationResponse(BaseModel):
    quoted_quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    unit_price: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=18, decimal_places=2)
    delivery_days: int = Field(default=0, ge=0, le=3650)
    valid_until: date
    notes: str | None = Field(default=None, max_length=2000)
