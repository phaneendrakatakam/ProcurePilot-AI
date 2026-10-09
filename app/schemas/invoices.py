import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class SupplierInvoiceItemCreate(BaseModel):
    purchase_order_item_id: uuid.UUID
    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    line_total: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def validate_line_total(self):
        expected = (self.quantity * self.unit_price).quantize(Decimal("0.01"))
        if self.line_total != expected:
            raise ValueError("Invoice line total must equal quantity multiplied by unit price.")
        return self


class SupplierInvoiceCreate(BaseModel):
    invoice_number: str = Field(min_length=1, max_length=80)
    vendor_id: uuid.UUID
    purchase_order_id: uuid.UUID
    invoice_date: date
    due_date: date
    currency: str = Field(min_length=3, max_length=3)
    subtotal: Decimal = Field(ge=0)
    tax_amount: Decimal = Field(ge=0)
    total_amount: Decimal = Field(ge=0)
    notes: str | None = None
    items: list[SupplierInvoiceItemCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_totals(self):
        line_total = sum((item.line_total for item in self.items), Decimal("0.00"))
        if self.subtotal != line_total:
            raise ValueError("Invoice subtotal must equal the sum of invoice line totals.")
        if self.total_amount != self.subtotal + self.tax_amount:
            raise ValueError("Invoice total must equal subtotal plus tax.")
        if self.due_date < self.invoice_date:
            raise ValueError("Invoice due date cannot be before the invoice date.")
        return self


class SupplierInvoiceItemResponse(BaseModel):
    id: uuid.UUID
    purchase_order_item_id: uuid.UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal

    model_config = {"from_attributes": True}


class SupplierInvoiceSummary(BaseModel):
    id: uuid.UUID
    invoice_number: str
    vendor_id: uuid.UUID
    supplier_name: str
    supplier_code: str
    purchase_order_id: uuid.UUID
    po_number: str
    invoice_date: date
    due_date: date
    currency: str
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    status: str
    created_by_user_id: uuid.UUID
    validated_at: datetime | None
    created_at: datetime
    payment_reference: str | None
    paid_at: datetime | None
    paid_by_user_id: uuid.UUID | None


class SupplierInvoiceDetail(SupplierInvoiceSummary):
    notes: str | None
    items: list[SupplierInvoiceItemResponse]


class InvoicePurchaseOrderItem(BaseModel):
    purchase_order_item_id: uuid.UUID
    name: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


class InvoicePurchaseOrder(BaseModel):
    purchase_order_id: uuid.UUID
    po_number: str
    vendor_id: uuid.UUID
    supplier_name: str
    supplier_code: str
    currency: str
    total_amount: Decimal
    payment_terms_days: int
    status: str
    items: list[InvoicePurchaseOrderItem]
