import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identity import Budget
from app.models.procurement import ClarificationTask, PurchaseRequest, RequestEvent


ALLOWED_CATEGORIES = {
    "IT_HARDWARE",
    "IT_SOFTWARE",
    "OFFICE_SUPPLIES",
    "PROFESSIONAL_SERVICES",
    "FACILITIES",
    "MARKETING",
    "OPERATIONS",
    "OTHER",
}


def money_round(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_request_total(request: PurchaseRequest) -> Decimal | None:
    if not request.items or any(item.unit_price is None for item in request.items):
        request.estimated_total = None
        return None

    total = sum((Decimal(item.line_total or 0) for item in request.items), Decimal("0.00"))
    request.estimated_total = money_round(total)
    return request.estimated_total


def missing_required_information(request: PurchaseRequest) -> list[tuple[str, str]]:
    missing: list[tuple[str, str]] = []
    if request.department_id is None:
        missing.append(("department", "Which department should own and fund this purchase request?"))
    if not request.category:
        missing.append(("category", "Select the procurement category for this request."))
    if not request.justification or len(request.justification.strip()) < 10:
        missing.append(("justification", "Provide a business justification of at least 10 characters."))
    if request.required_date is None:
        missing.append(("required_date", "When are the goods or services required?"))
    if not request.items:
        missing.append(("line_items", "Add at least one line item with a name and quantity."))
    else:
        for index, item in enumerate(request.items, start=1):
            item_name = (getattr(item, "name", None) or f"line item {index}").strip()
            quantity = getattr(item, "quantity", None)
            if quantity is None or Decimal(quantity) <= Decimal("0"):
                missing.append((
                    f"line_items.{index}.quantity",
                    f"Provide a quantity greater than zero for '{item_name}'.",
                ))

            unit_price = getattr(item, "unit_price", None)
            if unit_price is not None and Decimal(unit_price) <= Decimal("0"):
                missing.append((
                    f"line_items.{index}.unit_price",
                    f"Provide an estimated unit price greater than zero for '{item_name}', or leave it blank if supplier pricing is not yet known.",
                ))

            specifications = getattr(item, "specifications", None)
            has_specifications = False
            if isinstance(specifications, dict):
                has_specifications = any(str(value).strip() for value in specifications.values() if value is not None)
            elif specifications:
                has_specifications = bool(str(specifications).strip())

            if not has_specifications:
                missing.append((
                    f"line_items.{index}.specifications",
                    f"Provide specifications, scope, or key requirements for '{item_name}'.",
                ))
    return missing


def sync_clarification_tasks(
    request: PurchaseRequest,
    missing: list[tuple[str, str]],
    *,
    actor_user_id: uuid.UUID | None,
) -> None:
    missing_fields = {field for field, _ in missing}
    existing_open = {task.field_name: task for task in request.clarifications if task.status == "OPEN"}

    for field_name, question in missing:
        if field_name not in existing_open:
            request.clarifications.append(
                ClarificationTask(
                    field_name=field_name,
                    question=question,
                    status="OPEN",
                    created_by_actor_type="SYSTEM",
                )
            )

    now = datetime.now(timezone.utc)
    for field_name, task in existing_open.items():
        if field_name not in missing_fields:
            task.status = "RESOLVED"
            task.answer = task.answer or "Resolved through request update."
            task.answered_by_user_id = actor_user_id
            task.answered_at = now


def evaluate_budget(db: Session, request: PurchaseRequest) -> tuple[str, str, dict]:
    if request.department_id is None:
        return "NOT_CONFIGURED", "A department is required before budget validation can run.", {}

    requested_value = request.estimated_budget
    value_source = "estimated_budget"

    if requested_value is None:
        requested_value = request.estimated_total
        value_source = "estimated_total"

    if requested_value is None:
        return (
            "NOT_CHECKED",
            "No estimated budget or known line-item total was provided. Budget validation will run when a commercial estimate is available.",
            {"currency": request.currency, "value_source": None},
        )

    fiscal_year = request.required_date.year if request.required_date else date.today().year
    budget = db.scalar(
        select(Budget).where(
            Budget.department_id == request.department_id,
            Budget.fiscal_year == fiscal_year,
            Budget.is_active.is_(True),
        )
    )
    if not budget:
        return (
            "NOT_CONFIGURED",
            f"No active FY{fiscal_year} budget is configured for this department.",
            {"fiscal_year": fiscal_year, "requested": str(money_round(Decimal(requested_value))), "value_source": value_source},
        )

    available = money_round(Decimal(budget.allocated_amount) - Decimal(budget.consumed_amount))
    requested = money_round(Decimal(requested_value))
    details = {
        "budget_id": str(budget.id),
        "fiscal_year": fiscal_year,
        "allocated": str(budget.allocated_amount),
        "consumed": str(budget.consumed_amount),
        "available": str(available),
        "requested": str(requested),
        "value_source": value_source,
        "currency": budget.currency,
    }
    if requested <= available:
        return "PASS", f"Request is within the available {budget.currency} budget ({available} remaining before this request).", details
    return "FAIL", f"Request exceeds available {budget.currency} budget by {money_round(requested - available)}.", details


def evaluate_policy(request: PurchaseRequest) -> tuple[str, str, dict]:
    category = (request.category or "").upper()
    if category not in ALLOWED_CATEGORIES:
        return "FAIL", f"Category '{category}' is not eligible under the current procurement category policy.", {"category": category}

    if request.required_date and request.required_date < date.today():
        return "FAIL", "Required date cannot be in the past.", {"required_date": request.required_date.isoformat()}

    flags: list[str] = []
    policy_value = request.estimated_budget if request.estimated_budget is not None else request.estimated_total

    if policy_value is None:
        flags.append("PRICING_PENDING")
    elif Decimal(policy_value) >= Decimal("500000"):
        flags.append("HIGH_VALUE_APPROVAL_REQUIRED")

    if request.required_date and (request.required_date - date.today()).days <= 3:
        flags.append("EXPEDITED_TIMELINE")

    message = "Deterministic policy checks passed."
    if flags:
        message += " Downstream workflow flags: " + ", ".join(flags) + "."
    return "PASS", message, {"flags": flags, "category": category}


def append_request_event(
    request: PurchaseRequest,
    *,
    actor_type: str,
    event_type: str,
    actor_user_id: uuid.UUID | None = None,
    from_status: str | None = None,
    to_status: str | None = None,
    details: dict | None = None,
) -> RequestEvent:
    event = RequestEvent(
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        details=details,
    )
    request.events.append(event)
    return event
