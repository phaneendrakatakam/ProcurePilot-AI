import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class RoleSummary(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=12, max_length=256)
    department_id: uuid.UUID | None = None
    role_codes: list[str] = Field(default_factory=list)
    is_active: bool = True


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    password: str | None = Field(default=None, min_length=12, max_length=256)
    department_id: uuid.UUID | None = None
    role_codes: list[str] | None = None
    is_active: bool | None = None


class UserDetail(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    department_id: uuid.UUID | None
    roles: list[str]
    created_at: datetime
    updated_at: datetime


class DepartmentCreate(BaseModel):
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=120)
    is_active: bool = True


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    is_active: bool | None = None


class DepartmentResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetCreate(BaseModel):
    department_id: uuid.UUID
    fiscal_year: int = Field(ge=2020, le=2100)
    currency: str = Field(default="INR", min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    allocated_amount: Decimal = Field(ge=Decimal("0"))
    consumed_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    is_active: bool = True

    @model_validator(mode="after")
    def validate_amounts(self):
        if self.consumed_amount > self.allocated_amount:
            raise ValueError("consumed_amount cannot exceed allocated_amount")
        self.currency = self.currency.upper()
        return self


class BudgetUpdate(BaseModel):
    currency: str | None = Field(default=None, min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    allocated_amount: Decimal | None = Field(default=None, ge=Decimal("0"))
    consumed_amount: Decimal | None = Field(default=None, ge=Decimal("0"))
    is_active: bool | None = None

    @model_validator(mode="after")
    def normalize_currency(self):
        if self.currency is not None:
            self.currency = self.currency.upper()
        return self


class BudgetResponse(BaseModel):
    id: uuid.UUID
    department_id: uuid.UUID
    fiscal_year: int
    currency: str
    allocated_amount: Decimal
    consumed_amount: Decimal
    available_amount: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


class VendorCreate(BaseModel):
    vendor_code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    legal_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    contact_person: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=500)
    capabilities: str | None = Field(default=None, max_length=500)
    payment_terms_days: int = Field(default=30, ge=0, le=365)
    reliability_score: Decimal = Field(default=Decimal("75.00"), ge=Decimal("0"), le=Decimal("100"))
    is_active: bool = True


class VendorUpdate(BaseModel):
    legal_name: str | None = Field(default=None, min_length=2, max_length=200)
    email: EmailStr | None = None
    contact_person: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=500)
    capabilities: str | None = Field(default=None, max_length=500)
    payment_terms_days: int | None = Field(default=None, ge=0, le=365)
    reliability_score: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("100"))
    is_active: bool | None = None


class VendorResponse(BaseModel):
    id: uuid.UUID
    vendor_code: str
    legal_name: str
    email: str
    contact_person: str | None
    phone: str | None
    address: str | None
    capabilities: str | None
    payment_terms_days: int
    reliability_score: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    actor_type: str
    actor_user_id: uuid.UUID | None
    actor_user_name: str | None = None
    action: str
    entity_type: str
    entity_id: str
    details: dict | None
    created_at: datetime
