import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PurchaseRequestItemInput(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=700)
    quantity: Decimal = Field(gt=Decimal("0"), max_digits=12, decimal_places=2)
    unit_price: Decimal | None = Field(default=None, ge=Decimal("0"), max_digits=18, decimal_places=2)
    specifications: dict | None = None


class PurchaseRequestCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    category: str | None = Field(default=None, max_length=80)
    justification: str | None = None
    required_date: date | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    estimated_budget: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=18, decimal_places=2)
    source_text: str | None = None
    items: list[PurchaseRequestItemInput] = Field(default_factory=list)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else None

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None


class PurchaseRequestUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    category: str | None = Field(default=None, max_length=80)
    justification: str | None = None
    required_date: date | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    estimated_budget: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=18, decimal_places=2)
    source_text: str | None = None
    items: list[PurchaseRequestItemInput] | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else None

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None


class PurchaseRequestItemResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    quantity: Decimal
    unit_price: Decimal | None
    line_total: Decimal | None
    specifications: dict | None

    model_config = ConfigDict(from_attributes=True)


class ClarificationTaskResponse(BaseModel):
    id: uuid.UUID
    field_name: str
    question: str
    status: str
    answer: str | None
    created_by_actor_type: str
    answered_by_user_id: uuid.UUID | None
    created_at: datetime
    answered_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class RequestEventResponse(BaseModel):
    id: uuid.UUID
    actor_type: str
    actor_user_id: uuid.UUID | None
    event_type: str
    from_status: str | None
    to_status: str | None
    details: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseRequestSummary(BaseModel):
    id: uuid.UUID
    request_number: str
    requester_id: uuid.UUID
    department_id: uuid.UUID | None
    title: str
    category: str | None
    required_date: date | None
    currency: str | None
    estimated_total: Decimal | None
    estimated_budget: Decimal | None
    status: str
    budget_check_status: str
    policy_check_status: str
    line_count: int
    open_clarifications: int
    created_at: datetime
    updated_at: datetime


class PurchaseRequestDetail(PurchaseRequestSummary):
    justification: str | None
    source_text: str | None
    ai_structured: bool
    budget_check_message: str | None
    policy_check_message: str | None
    submitted_at: datetime | None
    items: list[PurchaseRequestItemResponse]
    clarifications: list[ClarificationTaskResponse]
    events: list[RequestEventResponse]


class ClarificationAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=2000)
