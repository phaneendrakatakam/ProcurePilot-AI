import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class GoodsReceiptItemCreate(BaseModel):
    purchase_order_item_id: uuid.UUID
    received_quantity: Decimal = Field(gt=0)
    accepted_quantity: Decimal = Field(ge=0)
    rejected_quantity: Decimal = Field(ge=0)
    rejection_reason: str | None = None

    @model_validator(mode="after")
    def validate_quantity_split(self):
        if self.accepted_quantity + self.rejected_quantity != self.received_quantity:
            raise ValueError("Accepted quantity plus rejected quantity must equal received quantity.")
        if self.rejected_quantity > 0 and not (self.rejection_reason or "").strip():
            raise ValueError("A rejection reason is required when rejected quantity is greater than zero.")
        return self


class GoodsReceiptCreate(BaseModel):
    purchase_order_id: uuid.UUID
    receipt_date: date
    delivery_reference: str | None = None
    notes: str | None = None
    items: list[GoodsReceiptItemCreate] = Field(min_length=1)


class GoodsReceiptItemResponse(BaseModel):
    id: uuid.UUID
    purchase_order_item_id: uuid.UUID
    item_name: str | None = None
    received_quantity: Decimal
    accepted_quantity: Decimal
    rejected_quantity: Decimal
    rejection_reason: str | None

    model_config = {"from_attributes": True}


class GoodsReceiptSummary(BaseModel):
    id: uuid.UUID
    receipt_number: str
    purchase_order_id: uuid.UUID
    po_number: str
    status: str
    receipt_date: date
    delivery_reference: str | None
    received_by_user_id: uuid.UUID
    received_by_name: str | None = None
    posted_at: datetime | None
    created_at: datetime


class GoodsReceiptDetail(GoodsReceiptSummary):
    notes: str | None
    items: list[GoodsReceiptItemResponse]


class GoodsReceiptPostResponse(GoodsReceiptDetail):
    pass


class GoodsReceiptOpenItem(BaseModel):
    purchase_order_item_id: uuid.UUID
    name: str
    ordered_quantity: Decimal
    received_quantity: Decimal
    remaining_quantity: Decimal
    unit_price: Decimal
    currency: str


class GoodsReceiptOpenPurchaseOrder(BaseModel):
    purchase_order_id: uuid.UUID
    po_number: str
    request_number: str
    supplier_name: str
    supplier_code: str
    currency: str
    required_date: date | None
    delivery_days: int
    status: str
    receiving_status: str
    items: list[GoodsReceiptOpenItem]
