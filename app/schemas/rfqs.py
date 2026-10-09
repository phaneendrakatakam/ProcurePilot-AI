import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class RFQCreate(BaseModel):
    request_id: uuid.UUID
    vendor_ids: list[uuid.UUID] = Field(min_length=1, max_length=25)
    response_deadline: datetime
    instructions: str | None = Field(default=None, max_length=2000)

    @field_validator("vendor_ids")
    @classmethod
    def unique_vendors(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Supplier selection contains duplicates")
        return value


class RFQSupplierResponse(BaseModel):
    id: uuid.UUID
    vendor_id: uuid.UUID
    vendor_code: str
    vendor_name: str
    email: str
    status: str
    sent_at: datetime | None


class RFQSummary(BaseModel):
    id: uuid.UUID
    rfq_number: str
    request_id: uuid.UUID
    request_number: str
    request_title: str
    status: str
    response_deadline: datetime
    supplier_count: int
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RFQDetail(RFQSummary):
    instructions: str | None
    suppliers: list[RFQSupplierResponse]
