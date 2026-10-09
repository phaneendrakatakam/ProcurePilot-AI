import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_any_permissions, require_permissions
from app.core.database import get_db
from app.models.governance import ActorType
from app.models.identity import Budget, Department, User, Vendor
from app.schemas.admin import (
    BudgetCreate,
    BudgetResponse,
    BudgetUpdate,
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    VendorCreate,
    VendorResponse,
    VendorUpdate,
)
from app.services.audit import record_audit_event

router = APIRouter(prefix="/admin/master-data", tags=["master-data"])


def _budget_response(budget: Budget) -> BudgetResponse:
    return BudgetResponse(
        id=budget.id,
        department_id=budget.department_id,
        fiscal_year=budget.fiscal_year,
        currency=budget.currency,
        allocated_amount=budget.allocated_amount,
        consumed_amount=budget.consumed_amount,
        available_amount=budget.allocated_amount - budget.consumed_amount,
        is_active=budget.is_active,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
    )


def _commit_or_conflict(db: Session, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=detail)


@router.get("/departments", response_model=list[DepartmentResponse])
def list_departments(
    _: User = Depends(require_permissions("master_data.manage")),
    db: Session = Depends(get_db),
):
    return list(db.scalars(select(Department).order_by(Department.code)).all())


@router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    actor: User = Depends(require_permissions("master_data.manage")),
    db: Session = Depends(get_db),
):
    department = Department(
        code=payload.code.strip().upper(),
        name=payload.name.strip(),
        is_active=payload.is_active,
    )
    db.add(department)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Department code or name already exists")
    record_audit_event(
        db,
        actor_type=ActorType.HUMAN,
        actor_user_id=actor.id,
        action="DEPARTMENT_CREATED",
        entity_type="department",
        entity_id=str(department.id),
        details={"code": department.code, "name": department.name},
    )
    _commit_or_conflict(db, "Department code or name already exists")
    db.refresh(department)
    return department


@router.patch("/departments/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: uuid.UUID,
    payload: DepartmentUpdate,
    actor: User = Depends(require_permissions("master_data.manage")),
    db: Session = Depends(get_db),
):
    department = db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    changes: dict[str, object] = {}
    if payload.name is not None:
        department.name = payload.name.strip()
        changes["name"] = department.name
    if payload.is_active is not None:
        department.is_active = payload.is_active
        changes["is_active"] = payload.is_active
    record_audit_event(
        db,
        actor_type=ActorType.HUMAN,
        actor_user_id=actor.id,
        action="DEPARTMENT_UPDATED",
        entity_type="department",
        entity_id=str(department.id),
        details=changes,
    )
    _commit_or_conflict(db, "Department name already exists")
    db.refresh(department)
    return department


@router.get("/budgets", response_model=list[BudgetResponse])
def list_budgets(
    _: User = Depends(require_permissions("master_data.manage")),
    db: Session = Depends(get_db),
):
    budgets = db.scalars(select(Budget).order_by(Budget.fiscal_year.desc())).all()
    return [_budget_response(budget) for budget in budgets]


@router.post("/budgets", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    payload: BudgetCreate,
    actor: User = Depends(require_permissions("master_data.manage")),
    db: Session = Depends(get_db),
):
    if db.get(Department, payload.department_id) is None:
        raise HTTPException(status_code=400, detail="Department not found")
    budget = Budget(
        department_id=payload.department_id,
        fiscal_year=payload.fiscal_year,
        currency=payload.currency,
        allocated_amount=payload.allocated_amount,
        consumed_amount=payload.consumed_amount,
        is_active=payload.is_active,
    )
    db.add(budget)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A budget already exists for this department and fiscal year")
    record_audit_event(
        db,
        actor_type=ActorType.HUMAN,
        actor_user_id=actor.id,
        action="BUDGET_CREATED",
        entity_type="budget",
        entity_id=str(budget.id),
        details={
            "department_id": str(budget.department_id),
            "fiscal_year": budget.fiscal_year,
            "allocated_amount": str(budget.allocated_amount),
        },
    )
    _commit_or_conflict(db, "A budget already exists for this department and fiscal year")
    db.refresh(budget)
    return _budget_response(budget)


@router.patch("/budgets/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: uuid.UUID,
    payload: BudgetUpdate,
    actor: User = Depends(require_permissions("master_data.manage")),
    db: Session = Depends(get_db),
):
    budget = db.get(Budget, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    new_allocated = payload.allocated_amount if payload.allocated_amount is not None else budget.allocated_amount
    new_consumed = payload.consumed_amount if payload.consumed_amount is not None else budget.consumed_amount
    if new_consumed > new_allocated:
        raise HTTPException(status_code=400, detail="consumed_amount cannot exceed allocated_amount")

    changes: dict[str, object] = {}
    for field in ("currency", "allocated_amount", "consumed_amount", "is_active"):
        value = getattr(payload, field)
        if value is not None:
            setattr(budget, field, value)
            changes[field] = str(value) if isinstance(value, Decimal) else value

    record_audit_event(
        db,
        actor_type=ActorType.HUMAN,
        actor_user_id=actor.id,
        action="BUDGET_UPDATED",
        entity_type="budget",
        entity_id=str(budget.id),
        details=changes,
    )
    db.commit()
    db.refresh(budget)
    return _budget_response(budget)


@router.get("/vendors", response_model=list[VendorResponse])
def list_vendors(
    _: User = Depends(require_any_permissions("master_data.manage", "sourcing.manage")),
    db: Session = Depends(get_db),
):
    return list(db.scalars(select(Vendor).order_by(Vendor.vendor_code)).all())


@router.post("/vendors", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
def create_vendor(
    payload: VendorCreate,
    actor: User = Depends(require_permissions("master_data.manage")),
    db: Session = Depends(get_db),
):
    vendor = Vendor(
        vendor_code=payload.vendor_code.strip().upper(),
        legal_name=payload.legal_name.strip(),
        email=str(payload.email).lower(),
        payment_terms_days=payload.payment_terms_days,
        reliability_score=payload.reliability_score,
        is_active=payload.is_active,
    )
    db.add(vendor)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Vendor code already exists")
    record_audit_event(
        db,
        actor_type=ActorType.HUMAN,
        actor_user_id=actor.id,
        action="VENDOR_CREATED",
        entity_type="vendor",
        entity_id=str(vendor.id),
        details={"vendor_code": vendor.vendor_code, "legal_name": vendor.legal_name},
    )
    _commit_or_conflict(db, "Vendor code already exists")
    db.refresh(vendor)
    return vendor


@router.patch("/vendors/{vendor_id}", response_model=VendorResponse)
def update_vendor(
    vendor_id: uuid.UUID,
    payload: VendorUpdate,
    actor: User = Depends(require_permissions("master_data.manage")),
    db: Session = Depends(get_db),
):
    vendor = db.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    changes: dict[str, object] = {}
    for field in ("legal_name", "email", "contact_person", "phone", "address", "capabilities", "payment_terms_days", "reliability_score", "is_active"):
        value = getattr(payload, field)
        if value is not None:
            if field == "email":
                value = str(value).lower()
            if field in ("legal_name", "contact_person", "phone", "address", "capabilities"):
                value = value.strip()
            setattr(vendor, field, value)
            changes[field] = str(value) if isinstance(value, Decimal) else value

    record_audit_event(
        db,
        actor_type=ActorType.HUMAN,
        actor_user_id=actor.id,
        action="VENDOR_UPDATED",
        entity_type="vendor",
        entity_id=str(vendor.id),
        details=changes,
    )
    db.commit()
    db.refresh(vendor)
    return vendor
