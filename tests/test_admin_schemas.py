import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.admin import BudgetCreate, UserCreate, VendorCreate


def test_budget_rejects_consumed_above_allocated():
    with pytest.raises(ValidationError):
        BudgetCreate(
            department_id=uuid.uuid4(),
            fiscal_year=2026,
            allocated_amount=Decimal("1000.00"),
            consumed_amount=Decimal("1000.01"),
        )


def test_budget_normalizes_currency():
    budget = BudgetCreate(
        department_id=uuid.uuid4(),
        fiscal_year=2026,
        currency="inr",
        allocated_amount=Decimal("250000.00"),
    )
    assert budget.currency == "INR"


def test_user_requires_strong_minimum_length_password():
    with pytest.raises(ValidationError):
        UserCreate(
            email="employee@example.com",
            full_name="Example Employee",
            password="short",
        )


def test_vendor_score_is_bounded():
    with pytest.raises(ValidationError):
        VendorCreate(
            vendor_code="V-100",
            legal_name="Example Vendor Pvt Ltd",
            email="vendor@example.com",
            reliability_score=Decimal("100.01"),
        )


def test_vendor_contact_fields_are_optional():
    vendor = VendorCreate(
        vendor_code="V-101",
        legal_name="Example Vendor Pvt Ltd",
        email="vendor@example.com",
    )
    assert vendor.contact_person is None
    assert vendor.phone is None
    assert vendor.address is None
    assert vendor.capabilities is None


def test_vendor_capabilities_length_is_bounded():
    with pytest.raises(ValidationError):
        VendorCreate(
            vendor_code="V-102",
            legal_name="Example Vendor Pvt Ltd",
            email="vendor@example.com",
            capabilities="x" * 501,
        )
