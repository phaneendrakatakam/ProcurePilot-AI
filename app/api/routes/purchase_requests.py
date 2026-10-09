import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies.auth import get_current_user, require_permissions
from app.core.database import get_db
from app.models.governance import ActorType
from app.models.goods_receipts import GoodsReceipt, GoodsReceiptItem
from app.models.invoices import SupplierInvoice
from app.models.invoice_matching import SupplierInvoiceMatch
from app.models.identity import User
from app.models.procurement import (
    ClarificationTask,
    PurchaseRequest,
    PurchaseRequestApproval,
    PurchaseRequestItem,
    RequestEvent, RFQ, SupplierSelection, PurchaseOrder, PurchaseOrderItem,
)
from app.schemas.purchase_requests import (
    ClarificationAnswer,
    ClarificationTaskResponse,
    PurchaseRequestCreate,
    PurchaseRequestDetail,
    PurchaseRequestItemResponse,
    PurchaseRequestSummary,
    PurchaseRequestUpdate,
    RequestEventResponse,
)
from app.services.audit import record_audit_event
from app.services.auth import get_permission_codes
from app.services.purchase_requests import (
    append_request_event,
    calculate_request_total,
    evaluate_budget,
    evaluate_policy,
    missing_required_information,
    money_round,
    sync_clarification_tasks,
)

router = APIRouter(prefix="/purchase-requests", tags=["purchase-requests"])


def _load_request(db: Session, request_id: uuid.UUID) -> PurchaseRequest | None:
    return db.scalar(
        select(PurchaseRequest)
        .options(
            selectinload(PurchaseRequest.items),
            selectinload(PurchaseRequest.clarifications),
            selectinload(PurchaseRequest.events),
            selectinload(PurchaseRequest.approvals),
        )
        .where(PurchaseRequest.id == request_id)
    )


def _can_read(user: User, request: PurchaseRequest) -> bool:
    permissions = set(get_permission_codes(user))

    if "purchase_requests.read_all" in permissions:
        return True

    if (
        "purchase_requests.read_department" in permissions
        and user.department_id
        and request.department_id == user.department_id
    ):
        return True

    if "purchase_requests.read_own" in permissions and request.requester_id == user.id:
        return True

    # An assigned approver may review the purchase request for their
    # pending approval without receiving general request-read access.
    if any(
        approval.approver_user_id == user.id
        and approval.status == "PENDING"
        for approval in request.approvals
    ):
        return True

    return False


def _require_read(user: User, request: PurchaseRequest) -> None:
    if not _can_read(user, request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this purchase request")


def _require_owner(user: User, request: PurchaseRequest) -> None:
    if request.requester_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the requester can change or submit this request")


def _request_number() -> str:
    now = datetime.now(timezone.utc)
    return f"PR-{now.year}-{uuid.uuid4().hex[:8].upper()}"


def _apply_items(request: PurchaseRequest, payload_items) -> None:
    request.items.clear()
    for item in payload_items:
        line_total = money_round(Decimal(item.quantity) * Decimal(item.unit_price)) if item.unit_price is not None else None
        request.items.append(
            PurchaseRequestItem(
                name=item.name.strip(),
                description=item.description.strip() if item.description else None,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=line_total,
                specifications=item.specifications,
            )
        )
    calculate_request_total(request)


def _summary(request: PurchaseRequest) -> PurchaseRequestSummary:
    return PurchaseRequestSummary(
        id=request.id,
        request_number=request.request_number,
        requester_id=request.requester_id,
        department_id=request.department_id,
        title=request.title,
        category=request.category,
        required_date=request.required_date,
        currency=request.currency,
        estimated_total=request.estimated_total,
        estimated_budget=request.estimated_budget,
        status=request.status,
        budget_check_status=request.budget_check_status,
        policy_check_status=request.policy_check_status,
        line_count=len(request.items),
        open_clarifications=sum(1 for task in request.clarifications if task.status == "OPEN"),
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


def _detail(request: PurchaseRequest) -> PurchaseRequestDetail:
    base = _summary(request).model_dump()
    return PurchaseRequestDetail(
        **base,
        justification=request.justification,
        source_text=request.source_text,
        ai_structured=request.ai_structured,
        budget_check_message=request.budget_check_message,
        policy_check_message=request.policy_check_message,
        submitted_at=request.submitted_at,
        items=[PurchaseRequestItemResponse.model_validate(item) for item in request.items],
        clarifications=[ClarificationTaskResponse.model_validate(task) for task in request.clarifications],
        events=[RequestEventResponse.model_validate(event) for event in request.events],
    )


@router.post("", response_model=PurchaseRequestDetail, status_code=status.HTTP_201_CREATED)
def create_purchase_request(
    payload: PurchaseRequestCreate,
    actor: User = Depends(require_permissions("purchase_requests.create")),
    db: Session = Depends(get_db),
) -> PurchaseRequestDetail:
    request = PurchaseRequest(
        request_number=_request_number(),
        requester_id=actor.id,
        department_id=actor.department_id,
        title=payload.title.strip(),
        category=payload.category,
        justification=payload.justification.strip() if payload.justification else None,
        required_date=payload.required_date,
        currency=payload.currency or "INR",
        estimated_budget=payload.estimated_budget,
        source_text=payload.source_text.strip() if payload.source_text else None,
        status="DRAFT",
    )
    db.add(request)
    db.flush()
    _apply_items(request, payload.items)
    append_request_event(request, actor_type="HUMAN", actor_user_id=actor.id, event_type="REQUEST_CREATED", to_status="DRAFT")
    record_audit_event(
        db,
        actor_type=ActorType.HUMAN,
        actor_user_id=actor.id,
        action="PURCHASE_REQUEST_CREATED",
        entity_type="purchase_request",
        entity_id=str(request.id),
        details={"request_number": request.request_number, "status": request.status},
    )
    db.commit()
    return _detail(_load_request(db, request.id))


@router.get("", response_model=list[PurchaseRequestSummary])
def list_purchase_requests(
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PurchaseRequestSummary]:
    permissions = set(get_permission_codes(actor))
    stmt = select(PurchaseRequest).options(
        selectinload(PurchaseRequest.items), selectinload(PurchaseRequest.clarifications)
    ).order_by(PurchaseRequest.created_at.desc())

    if "purchase_requests.read_all" in permissions:
        pass
    elif "purchase_requests.read_department" in permissions and actor.department_id:
        stmt = stmt.where(PurchaseRequest.department_id == actor.department_id)
    elif "purchase_requests.read_own" in permissions:
        stmt = stmt.where(PurchaseRequest.requester_id == actor.id)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return [_summary(request) for request in db.scalars(stmt).unique().all()]


@router.get("/sourcing/queue", response_model=list[PurchaseRequestSummary])
def list_sourcing_queue(
    q: str | None = Query(default=None, max_length=120),
    queue_status: str = Query(default="active", alias="status"),
    _: User = Depends(require_permissions("sourcing.manage")),
    db: Session = Depends(get_db),
):
    """Return purchase requests currently actionable by the sourcing team."""
    allowed_statuses = {"active": {"READY_FOR_SOURCING", "SOURCING"}, "ready": {"READY_FOR_SOURCING"}, "sourcing": {"SOURCING"}}
    statuses = allowed_statuses.get(queue_status.lower())
    if statuses is None:
        raise HTTPException(status_code=400, detail="status must be active, ready, or sourcing")

    stmt = (
        select(PurchaseRequest)
        .options(selectinload(PurchaseRequest.items), selectinload(PurchaseRequest.clarifications))
        .where(PurchaseRequest.status.in_(statuses))
        .order_by(PurchaseRequest.required_date.asc().nulls_last(), PurchaseRequest.updated_at.desc())
    )
    search = q.strip() if q else ""
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(
            PurchaseRequest.request_number.ilike(pattern),
            PurchaseRequest.title.ilike(pattern),
            PurchaseRequest.category.ilike(pattern),
        ))

    return [_summary(request) for request in db.scalars(stmt).all()]


@router.post("/{request_id}/start-sourcing", response_model=PurchaseRequestDetail)
def start_sourcing(
    request_id: uuid.UUID,
    actor: User = Depends(require_permissions("sourcing.manage")),
    db: Session = Depends(get_db),
) -> PurchaseRequestDetail:
    request = _load_request(db, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Purchase request not found")
    if request.status != "READY_FOR_SOURCING":
        raise HTTPException(status_code=409, detail=f"Request cannot enter sourcing from status {request.status}")

    previous_status = request.status
    request.status = "SOURCING"
    append_request_event(
        request,
        actor_type="HUMAN",
        actor_user_id=actor.id,
        event_type="SOURCING_STARTED",
        from_status=previous_status,
        to_status="SOURCING",
        details={"started_by": actor.full_name},
    )
    record_audit_event(
        db,
        actor_type=ActorType.HUMAN,
        actor_user_id=actor.id,
        action="PURCHASE_REQUEST_SOURCING_STARTED",
        entity_type="purchase_request",
        entity_id=str(request.id),
        details={"request_number": request.request_number},
    )
    db.commit()
    return _detail(_load_request(db, request.id))


def _stage(label: str, state: str, detail: str = "") -> dict:
    return {"label": label, "state": state, "detail": detail}


@router.get("/{request_id}/lifecycle")
def get_purchase_request_lifecycle(
    request_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Read-only end-to-end operational state; the PR approval status stays immutable."""
    request = _load_request(db, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Purchase request not found")
    db.scalars(select(PurchaseRequestApproval).where(PurchaseRequestApproval.purchase_request_id == request_id)).all()
    _require_read(actor, request)
    rfqs = db.scalars(select(RFQ).where(RFQ.request_id == request_id)).all()
    rfq_ids = [r.id for r in rfqs]
    selections = db.scalars(select(SupplierSelection).where(SupplierSelection.rfq_id.in_(rfq_ids))).all() if rfq_ids else []
    approvals = db.scalars(select(PurchaseRequestApproval).where(PurchaseRequestApproval.purchase_request_id == request_id).order_by(PurchaseRequestApproval.sequence)).all()
    po = db.scalar(select(PurchaseOrder).options(selectinload(PurchaseOrder.items)).where(PurchaseOrder.purchase_request_id == request_id).order_by(PurchaseOrder.created_at.desc()))
    receipt_items = []
    invoices = []
    if po is not None:
        receipt_items = db.execute(select(GoodsReceiptItem.purchase_order_item_id, GoodsReceiptItem.accepted_quantity)
            .join(GoodsReceipt, GoodsReceipt.id == GoodsReceiptItem.goods_receipt_id)
            .where(GoodsReceipt.purchase_order_id == po.id, GoodsReceipt.status == "POSTED")).all()
        invoices = db.scalars(select(SupplierInvoice).where(SupplierInvoice.purchase_order_id == po.id).order_by(SupplierInvoice.created_at.desc())).all()
    accepted_by_line = {}
    for item_id, qty in receipt_items:
        accepted_by_line[item_id] = accepted_by_line.get(item_id, Decimal("0")) + Decimal(qty)
    has_receipt = bool(receipt_items)
    fully_received = bool(po and po.items and all(accepted_by_line.get(item.id, Decimal("0")) >= item.quantity for item in po.items))
    matched = False
    paid = False
    payment_reference = None
    for invoice in invoices:
        match = db.scalar(select(SupplierInvoiceMatch).where(SupplierInvoiceMatch.invoice_id == invoice.id))
        matched = matched or bool(match and match.result == "MATCHED")
        if invoice.status == "PAID":
            paid = True
            payment_reference = invoice.payment_reference
    sourcing = bool(rfqs or selections) or request.status in {"SOURCING", "SUPPLIER_SELECTED", "PENDING_APPROVAL", "APPROVED"}
    approvals_complete = bool(approvals and all(a.status == "APPROVED" for a in approvals))
    steps = [
        _stage("Request created", "DONE", request.request_number),
        _stage("Request validated", "DONE" if request.budget_check_status == "PASS" and request.policy_check_status == "PASS" else "PENDING", "Budget and policy"),
        _stage("Sourcing & supplier", "DONE" if selections else "ACTIVE" if sourcing else "PENDING", "Supplier selected" if selections else "Awaiting selection"),
        _stage("Mandatory approvals", "DONE" if approvals_complete else "ACTIVE" if approvals else "PENDING", f"{sum(a.status == 'APPROVED' for a in approvals)} of 3 approved" if approvals else "Not routed"),
        _stage("Purchase order", "DONE" if po and po.status == "ISSUED" else "ACTIVE" if po else "PENDING", po.po_number if po else "Not created"),
        _stage("Goods received", "DONE" if fully_received else "ACTIVE" if has_receipt else "PENDING", "Accepted units fully received" if fully_received else "Awaiting posted receipt"),
        _stage("Invoice & 3-way match", "DONE" if matched else "ACTIVE" if invoices else "PENDING", "Matched" if matched else "Matching pending"),
        _stage("Payment finalized", "DONE" if paid else "PENDING", payment_reference or "Not yet paid"),
    ]
    return {"request_id": str(request.id), "request_status": request.status, "overall_status": "PAID" if paid else "IN_PROGRESS", "steps": steps}


@router.get("/{request_id}", response_model=PurchaseRequestDetail)
def get_purchase_request(
    request_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PurchaseRequestDetail:
    request = _load_request(db, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Purchase request not found")
    _require_read(actor, request)
    return _detail(request)


@router.patch("/{request_id}", response_model=PurchaseRequestDetail)
def update_purchase_request(
    request_id: uuid.UUID,
    payload: PurchaseRequestUpdate,
    actor: User = Depends(require_permissions("purchase_requests.create")),
    db: Session = Depends(get_db),
) -> PurchaseRequestDetail:
    request = _load_request(db, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Purchase request not found")
    _require_owner(actor, request)
    if request.status not in {"DRAFT", "NEEDS_CLARIFICATION", "BUDGET_EXCEPTION", "POLICY_EXCEPTION"}:
        raise HTTPException(status_code=409, detail=f"Request cannot be edited in status {request.status}")

    changes: dict[str, object] = {}
    for field in ("title", "category", "justification", "required_date", "currency", "estimated_budget", "source_text"):
        if field in payload.model_fields_set:
            value = getattr(payload, field)
            if isinstance(value, str):
                value = value.strip() or None
            setattr(request, field, value)
            changes[field] = value.isoformat() if hasattr(value, "isoformat") else value

    if payload.items is not None:
        _apply_items(request, payload.items)
        changes["line_count"] = len(request.items)
        changes["estimated_total"] = str(request.estimated_total)

    request.budget_check_status = "NOT_CHECKED"
    request.budget_check_message = None
    request.policy_check_status = "NOT_CHECKED"
    request.policy_check_message = None

    append_request_event(request, actor_type="HUMAN", actor_user_id=actor.id, event_type="REQUEST_UPDATED", details=changes)
    record_audit_event(
        db,
        actor_type=ActorType.HUMAN,
        actor_user_id=actor.id,
        action="PURCHASE_REQUEST_UPDATED",
        entity_type="purchase_request",
        entity_id=str(request.id),
        details=changes,
    )
    db.commit()
    return _detail(_load_request(db, request.id))


@router.post("/{request_id}/submit", response_model=PurchaseRequestDetail)
def submit_purchase_request(
    request_id: uuid.UUID,
    actor: User = Depends(require_permissions("purchase_requests.create")),
    db: Session = Depends(get_db),
) -> PurchaseRequestDetail:
    request = _load_request(db, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Purchase request not found")
    _require_owner(actor, request)
    if request.status not in {"DRAFT", "NEEDS_CLARIFICATION", "BUDGET_EXCEPTION", "POLICY_EXCEPTION"}:
        raise HTTPException(status_code=409, detail=f"Request cannot be submitted from status {request.status}")

    calculate_request_total(request)
    previous_status = request.status
    missing = missing_required_information(request)
    sync_clarification_tasks(request, missing, actor_user_id=actor.id)

    if missing:
        request.status = "NEEDS_CLARIFICATION"
        request.budget_check_status = "NOT_CHECKED"
        request.budget_check_message = None
        request.policy_check_status = "NOT_CHECKED"
        request.policy_check_message = None
        append_request_event(
            request,
            actor_type="SYSTEM",
            event_type="CLARIFICATION_REQUIRED",
            from_status=previous_status,
            to_status=request.status,
            details={"missing_fields": [field for field, _ in missing]},
        )
        record_audit_event(
            db,
            actor_type=ActorType.SYSTEM,
            action="PURCHASE_REQUEST_NEEDS_CLARIFICATION",
            entity_type="purchase_request",
            entity_id=str(request.id),
            details={"request_number": request.request_number, "missing_fields": [field for field, _ in missing]},
        )
        db.commit()
        return _detail(_load_request(db, request.id))

    request.submitted_at = datetime.now(timezone.utc)
    request.status = "SUBMITTED"
    append_request_event(
        request,
        actor_type="HUMAN",
        actor_user_id=actor.id,
        event_type="REQUEST_SUBMITTED",
        from_status=previous_status,
        to_status="SUBMITTED",
        details={"estimated_total": str(request.estimated_total), "currency": request.currency},
    )

    budget_status, budget_message, budget_details = evaluate_budget(db, request)
    request.budget_check_status = budget_status
    request.budget_check_message = budget_message
    append_request_event(request, actor_type="SYSTEM", event_type="BUDGET_CHECK_COMPLETED", details={"decision": budget_status, **budget_details})
    record_audit_event(
        db,
        actor_type=ActorType.SYSTEM,
        action="PURCHASE_REQUEST_BUDGET_CHECKED",
        entity_type="purchase_request",
        entity_id=str(request.id),
        details={"decision": budget_status, "message": budget_message, **budget_details},
    )

    policy_status, policy_message, policy_details = evaluate_policy(request)
    request.policy_check_status = policy_status
    request.policy_check_message = policy_message
    append_request_event(request, actor_type="SYSTEM", event_type="POLICY_CHECK_COMPLETED", details={"decision": policy_status, **policy_details})
    record_audit_event(
        db,
        actor_type=ActorType.SYSTEM,
        action="PURCHASE_REQUEST_POLICY_CHECKED",
        entity_type="purchase_request",
        entity_id=str(request.id),
        details={"decision": policy_status, "message": policy_message, **policy_details},
    )

    if budget_status == "FAIL":
        final_status = "BUDGET_EXCEPTION"
    elif policy_status != "PASS":
        final_status = "POLICY_EXCEPTION"
    elif budget_status in {"PASS", "NOT_CHECKED"}:
        final_status = "READY_FOR_SOURCING"
    else:
        final_status = "BUDGET_EXCEPTION"

    request.status = final_status
    append_request_event(
        request,
        actor_type="SYSTEM",
        event_type="REQUEST_VALIDATION_COMPLETED",
        from_status="SUBMITTED",
        to_status=final_status,
        details={"budget": budget_status, "policy": policy_status},
    )
    record_audit_event(
        db,
        actor_type=ActorType.SYSTEM,
        action="PURCHASE_REQUEST_VALIDATION_COMPLETED",
        entity_type="purchase_request",
        entity_id=str(request.id),
        details={"request_number": request.request_number, "status": final_status, "budget": budget_status, "policy": policy_status},
    )
    db.commit()
    return _detail(_load_request(db, request.id))


@router.post("/{request_id}/clarifications/{task_id}/answer", response_model=PurchaseRequestDetail)
def answer_clarification(
    request_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: ClarificationAnswer,
    actor: User = Depends(require_permissions("purchase_requests.create")),
    db: Session = Depends(get_db),
) -> PurchaseRequestDetail:
    request = _load_request(db, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Purchase request not found")
    _require_owner(actor, request)
    task = next((task for task in request.clarifications if task.id == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Clarification task not found")
    if task.status != "OPEN":
        raise HTTPException(status_code=409, detail="Clarification task is already closed")

    task.status = "ANSWERED"
    task.answer = payload.answer.strip()
    task.answered_by_user_id = actor.id
    task.answered_at = datetime.now(timezone.utc)
    append_request_event(
        request,
        actor_type="HUMAN",
        actor_user_id=actor.id,
        event_type="CLARIFICATION_ANSWERED",
        details={"field_name": task.field_name, "task_id": str(task.id)},
    )
    record_audit_event(
        db,
        actor_type=ActorType.HUMAN,
        actor_user_id=actor.id,
        action="PURCHASE_REQUEST_CLARIFICATION_ANSWERED",
        entity_type="purchase_request",
        entity_id=str(request.id),
        details={"field_name": task.field_name, "task_id": str(task.id)},
    )
    db.commit()
    return _detail(_load_request(db, request.id))
