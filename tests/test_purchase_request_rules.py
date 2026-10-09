from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from app.schemas.purchase_requests import PurchaseRequestCreate, PurchaseRequestItemInput
from app.services.purchase_requests import evaluate_policy, missing_required_information, money_round


def _request(**overrides):
    data = dict(
        department_id="dept",
        category="IT_HARDWARE",
        justification="New developers require standard engineering laptops.",
        required_date=date.today() + timedelta(days=10),
        items=[SimpleNamespace(name="Laptop", quantity=1, unit_price=Decimal("80000"), line_total=Decimal("80000"))],
        estimated_total=Decimal("80000"),
        estimated_budget=None,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def test_missing_information_detects_required_fields():
    request = _request(department_id=None, category=None, justification=None, required_date=None, items=[])
    fields = {field for field, _ in missing_required_information(request)}
    assert fields == {"department", "category", "justification", "required_date", "line_items"}


def test_policy_passes_normal_request():
    decision, message, details = evaluate_policy(_request())
    assert decision == "PASS"
    assert "passed" in message.lower()
    assert details["flags"] == []


def test_policy_rejects_past_required_date():
    decision, _, _ = evaluate_policy(_request(required_date=date.today() - timedelta(days=1)))
    assert decision == "FAIL"


def test_high_value_policy_flag_is_explainable_not_silent():
    decision, message, details = evaluate_policy(_request(estimated_total=Decimal("750000")))
    assert decision == "PASS"
    assert "HIGH_VALUE_APPROVAL_REQUIRED" in details["flags"]
    assert "Downstream workflow flags" in message


def test_purchase_request_schema_normalizes_currency_and_category():
    payload = PurchaseRequestCreate(
        title="Developer laptops",
        category="it_hardware",
        currency="inr",
        items=[PurchaseRequestItemInput(name="Laptop", quantity=2, unit_price=Decimal("80000"))],
    )
    assert payload.currency == "INR"
    assert payload.category == "IT_HARDWARE"
    assert money_round(payload.items[0].quantity * payload.items[0].unit_price) == Decimal("160000.00")


def test_missing_information_allows_unknown_price_but_requires_specs():
    item = SimpleNamespace(
        name="Raw material",
        quantity=Decimal("5"),
        unit_price=None,
        line_total=None,
        specifications=None,
    )
    request = _request(items=[item], estimated_total=None)
    fields = {field for field, _ in missing_required_information(request)}
    assert "line_items.1.unit_price" not in fields
    assert "line_items.1.specifications" in fields


def test_unknown_price_with_specifications_is_complete():
    item = SimpleNamespace(
        name="Raw material",
        quantity=Decimal("5"),
        unit_price=None,
        line_total=None,
        specifications={"notes": "Grade A industrial raw material; supplier to quote."},
    )
    request = _request(items=[item], estimated_total=None)
    fields = {field for field, _ in missing_required_information(request)}
    assert not any(field.startswith("line_items.") for field in fields)


def test_complete_line_item_does_not_create_line_clarifications():
    item = SimpleNamespace(
        name="Monitor",
        quantity=Decimal("5"),
        unit_price=Decimal("25000"),
        line_total=Decimal("125000"),
        specifications={"notes": "27-inch QHD USB-C monitor"},
    )
    request = _request(items=[item], estimated_total=Decimal("125000"))
    fields = {field for field, _ in missing_required_information(request)}
    assert not any(field.startswith("line_items.") for field in fields)


def test_policy_allows_request_when_pricing_is_pending():
    decision, message, details = evaluate_policy(_request(estimated_total=None))
    assert decision == "PASS"
    assert "PRICING_PENDING" in details["flags"]
    assert "passed" in message.lower()


def test_purchase_request_schema_allows_optional_currency_budget_and_unit_price():
    payload = PurchaseRequestCreate(
        title="Raw material sourcing",
        category="OPERATIONS",
        items=[PurchaseRequestItemInput(name="Raw material", quantity=10, unit_price=None)],
        currency=None,
        estimated_budget=None,
    )
    assert payload.currency is None
    assert payload.estimated_budget is None
    assert payload.items[0].unit_price is None
