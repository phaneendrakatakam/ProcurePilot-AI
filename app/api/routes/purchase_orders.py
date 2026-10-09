import secrets
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies.auth import require_permissions
from app.core.database import get_db
from app.models.governance import ActorType
from app.models.identity import User
from app.models.procurement import (
    PurchaseOrder, PurchaseOrderItem, PurchaseRequestApproval, RFQ, RFQSupplier,
    SupplierQuotation, SupplierQuotationItem, SupplierSelection,
)
from app.schemas.purchase_orders import PurchaseOrderCreate, PurchaseOrderDetail, PurchaseOrderSummary, PurchaseOrderItemResponse
from app.services.audit import record_audit_event
from app.services.purchase_requests import append_request_event
from app.services.supplier_email import build_purchase_order_email, send_email

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])


def _load(db: Session, po_id: uuid.UUID) -> PurchaseOrder | None:
    return db.scalar(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.request),
            selectinload(PurchaseOrder.vendor),
            selectinload(PurchaseOrder.supplier_selection).selectinload(SupplierSelection.rfq),
            selectinload(PurchaseOrder.items),
        )
        .where(PurchaseOrder.id == po_id)
    )


def _summary(po: PurchaseOrder) -> PurchaseOrderSummary:
    return PurchaseOrderSummary(
        id=po.id, po_number=po.po_number, purchase_request_id=po.purchase_request_id,
        request_number=po.request.request_number, supplier_selection_id=po.supplier_selection_id,
        vendor_id=po.vendor_id, supplier_code=po.vendor.vendor_code, supplier_name=po.vendor.legal_name,
        currency=po.currency, status=po.status, po_date=po.po_date, required_date=po.required_date,
        subtotal=po.subtotal, tax_amount=po.tax_amount, total_amount=po.total_amount,
        delivery_days=int(po.delivery_days), payment_terms_days=po.payment_terms_days,
        issued_at=po.issued_at,
        supplier_notification_status=po.supplier_notification_status,
        supplier_notification_sent_at=po.supplier_notification_sent_at,
        supplier_notification_error=po.supplier_notification_error,
        created_by_user_id=po.created_by_user_id,
    )


def _detail(po: PurchaseOrder) -> PurchaseOrderDetail:
    return PurchaseOrderDetail(
        **_summary(po).model_dump(), notes=po.notes,
        items=[PurchaseOrderItemResponse.model_validate(item, from_attributes=True) for item in po.items],
    )


@router.get("", response_model=list[PurchaseOrderSummary])
def list_purchase_orders(
    actor: User = Depends(require_permissions("sourcing.manage")),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.request),
            selectinload(PurchaseOrder.vendor),
            selectinload(PurchaseOrder.items),
        )
        .order_by(PurchaseOrder.created_at.desc())
    ).all()
    return [_summary(row) for row in rows]


@router.get("/{po_id}", response_model=PurchaseOrderDetail)
def get_purchase_order(
    po_id: uuid.UUID,
    actor: User = Depends(require_permissions("sourcing.manage")),
    db: Session = Depends(get_db),
):
    po = _load(db, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return _detail(po)


def _load_for_transition(db: Session, po_id: uuid.UUID) -> PurchaseOrder | None:
    return db.scalar(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.request), selectinload(PurchaseOrder.vendor))
        .where(PurchaseOrder.id == po_id)
    )


class PurchaseOrderTermsCorrection(BaseModel):
    payment_terms_days: int = Field(ge=0, le=3650)
    explanation: str = Field(min_length=10, max_length=500)


@router.patch("/{po_id}/payment-terms", response_model=PurchaseOrderDetail)
def correct_purchase_order_payment_terms(
    po_id: uuid.UUID,
    payload: PurchaseOrderTermsCorrection,
    actor: User = Depends(require_permissions("sourcing.manage")),
    db: Session = Depends(get_db),
):
    po = _load_for_transition(db, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status not in {"DRAFT", "PENDING_RELEASE"}:
        raise HTTPException(status_code=409, detail="Issued purchase orders are immutable; use a controlled amendment workflow.")
    actor_roles = {role.role.code for role in actor.roles}
    if po.status == "PENDING_RELEASE" and "PROCUREMENT_HEAD" not in actor_roles:
        raise HTTPException(status_code=403, detail="Only the Procurement Head can correct submitted PO terms")
    previous_terms = po.payment_terms_days
    po.payment_terms_days = payload.payment_terms_days
    record_audit_event(db, actor_type=ActorType.HUMAN, actor_user_id=actor.id,
        action="PURCHASE_ORDER_PAYMENT_TERMS_CORRECTED", entity_type="purchase_order", entity_id=str(po.id),
        details={"po_number": po.po_number, "old_days": previous_terms,
                 "new_days": po.payment_terms_days, "explanation": payload.explanation})
    append_request_event(po.request, actor_type="HUMAN", actor_user_id=actor.id,
        event_type="PURCHASE_ORDER_PAYMENT_TERMS_CORRECTED",
        details={"po_number": po.po_number, "old_days": previous_terms, "new_days": po.payment_terms_days})
    db.commit()
    return _detail(_load(db, po.id))


@router.post("/{po_id}/submit-release", response_model=PurchaseOrderDetail)
def submit_purchase_order_for_release(
    po_id: uuid.UUID,
    actor: User = Depends(require_permissions("sourcing.manage")),
    db: Session = Depends(get_db),
):
    po = _load_for_transition(db, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status != "DRAFT":
        raise HTTPException(status_code=409, detail=f"Only draft purchase orders can be submitted for release (current status: {po.status})")

    po.status = "PENDING_RELEASE"
    append_request_event(
        po.request, actor_type="HUMAN", actor_user_id=actor.id,
        event_type="PURCHASE_ORDER_SUBMITTED_FOR_RELEASE",
        from_status=po.request.status, to_status=po.request.status,
        details={"po_number": po.po_number, "purchase_order_id": str(po.id)},
    )
    record_audit_event(
        db, actor_type=ActorType.HUMAN, actor_user_id=actor.id,
        action="PURCHASE_ORDER_SUBMITTED_FOR_RELEASE", entity_type="purchase_order", entity_id=str(po.id),
        details={"po_number": po.po_number, "request_number": po.request.request_number},
    )
    db.commit()
    return _detail(_load(db, po.id))


@router.post("/{po_id}/release", response_model=PurchaseOrderDetail)
def release_purchase_order(
    po_id: uuid.UUID,
    actor: User = Depends(require_permissions("sourcing.manage")),
    db: Session = Depends(get_db),
):
    po = _load_for_transition(db, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    actor_roles = {role.role.code for role in actor.roles}
    if "PROCUREMENT_HEAD" not in actor_roles:
        raise HTTPException(status_code=403, detail="Only a Procurement Head can issue a purchase order")
    if po.status != "PENDING_RELEASE":
        raise HTTPException(status_code=409, detail=f"Only purchase orders pending release can be issued (current status: {po.status})")

    po.status = "ISSUED"
    po.issued_at = datetime.now(timezone.utc)
    po.supplier_notification_status = "PENDING"
    po.supplier_notification_sent_at = None
    po.supplier_notification_error = None
    append_request_event(
        po.request, actor_type="HUMAN", actor_user_id=actor.id,
        event_type="PURCHASE_ORDER_ISSUED",
        from_status=po.request.status, to_status=po.request.status,
        details={"po_number": po.po_number, "purchase_order_id": str(po.id)},
    )
    record_audit_event(
        db, actor_type=ActorType.HUMAN, actor_user_id=actor.id,
        action="PURCHASE_ORDER_ISSUED", entity_type="purchase_order", entity_id=str(po.id),
        details={"po_number": po.po_number, "request_number": po.request.request_number, "issued_at": po.issued_at.isoformat()},
    )
    db.commit()

    try:
        item_lines = [
            f"{item.name} — qty {item.quantity} — {po.currency} {item.unit_price} each"
            for item in po.items
        ]
        message = build_purchase_order_email(
            to_email=po.vendor.email,
            supplier_name=po.vendor.legal_name,
            po_number=po.po_number,
            request_title=po.request.title,
            currency=po.currency,
            total_amount=str(po.total_amount),
            subtotal=str(po.subtotal),
            tax_amount=str(po.tax_amount),
            delivery_days=int(po.delivery_days),
            payment_terms_days=po.payment_terms_days,
            required_date=po.required_date.isoformat() if po.required_date else None,
            item_lines=item_lines,
            notes=po.notes,
        )
        send_email(message)
        po.supplier_notification_status = "SENT"
        po.supplier_notification_sent_at = datetime.now(timezone.utc)
        po.supplier_notification_error = None
        record_audit_event(
            db, actor_type=ActorType.HUMAN, actor_user_id=actor.id,
            action="PURCHASE_ORDER_SUPPLIER_EMAIL_SENT", entity_type="purchase_order", entity_id=str(po.id),
            details={"po_number": po.po_number, "supplier_email": po.vendor.email},
        )
    except Exception as exc:
        po.supplier_notification_status = "FAILED"
        po.supplier_notification_error = str(exc)[:500]
        record_audit_event(
            db, actor_type=ActorType.HUMAN, actor_user_id=actor.id,
            action="PURCHASE_ORDER_SUPPLIER_EMAIL_FAILED", entity_type="purchase_order", entity_id=str(po.id),
            details={"po_number": po.po_number, "supplier_email": po.vendor.email, "error": str(exc)[:500]},
        )
    db.commit()
    return _detail(_load(db, po.id))


@router.post("/{po_id}/notify-supplier", response_model=PurchaseOrderDetail)
def notify_supplier_for_purchase_order(
    po_id: uuid.UUID,
    actor: User = Depends(require_permissions("sourcing.manage")),
    db: Session = Depends(get_db),
):
    """Retry supplier notification for an already-issued purchase order."""
    po = _load_for_transition(db, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status != "ISSUED":
        raise HTTPException(status_code=409, detail="Supplier notification can only be sent for an issued purchase order")
    if po.supplier_notification_status == "SENT":
        raise HTTPException(status_code=409, detail="The supplier has already been notified for this purchase order")

    try:
        item_lines = [
            f"{item.name} — qty {item.quantity} — {po.currency} {item.unit_price} each"
            for item in po.items
        ]
        message = build_purchase_order_email(
            to_email=po.vendor.email,
            supplier_name=po.vendor.legal_name,
            po_number=po.po_number,
            request_title=po.request.title,
            currency=po.currency,
            total_amount=str(po.total_amount),
            subtotal=str(po.subtotal),
            tax_amount=str(po.tax_amount),
            delivery_days=int(po.delivery_days),
            payment_terms_days=po.payment_terms_days,
            required_date=po.required_date.isoformat() if po.required_date else None,
            item_lines=item_lines,
            notes=po.notes,
        )
        send_email(message)
        po.supplier_notification_status = "SENT"
        po.supplier_notification_sent_at = datetime.now(timezone.utc)
        po.supplier_notification_error = None
        action = "PURCHASE_ORDER_SUPPLIER_EMAIL_SENT"
    except Exception as exc:
        po.supplier_notification_status = "FAILED"
        po.supplier_notification_error = str(exc)[:500]
        action = "PURCHASE_ORDER_SUPPLIER_EMAIL_FAILED"

    record_audit_event(
        db, actor_type=ActorType.HUMAN, actor_user_id=actor.id,
        action=action, entity_type="purchase_order", entity_id=str(po.id),
        details={"po_number": po.po_number, "supplier_email": po.vendor.email, "error": po.supplier_notification_error},
    )
    db.commit()
    return _detail(_load(db, po.id))

@router.post("", response_model=PurchaseOrderDetail, status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    payload: PurchaseOrderCreate,
    actor: User = Depends(require_permissions("sourcing.manage")),
    db: Session = Depends(get_db),
):
    payment_terms_days = int(payload.payment_terms_days)
    if payment_terms_days < 0 or payment_terms_days > 3650:
        raise HTTPException(status_code=422, detail="Payment terms must be between 0 and 3650 days")

    selection = db.scalar(
        select(SupplierSelection)
        .options(
            selectinload(SupplierSelection.rfq).selectinload(RFQ.request),
            selectinload(SupplierSelection.rfq_supplier).selectinload(RFQSupplier.vendor),
            selectinload(SupplierSelection.quotation).selectinload(SupplierQuotation.items).selectinload(SupplierQuotationItem.request_item),
        )
        .where(SupplierSelection.id == payload.supplier_selection_id)
    )
    if not selection:
        raise HTTPException(status_code=404, detail="Supplier selection not found")

    request = selection.rfq.request
    if request.status != "APPROVED":
        raise HTTPException(status_code=409, detail=f"Purchase order can only be created for an approved purchase request (current status: {request.status})")

    approvals = db.scalars(
        select(PurchaseRequestApproval)
        .where(PurchaseRequestApproval.purchase_request_id == request.id)
        .order_by(PurchaseRequestApproval.sequence.asc())
    ).all()
    if not approvals or any(a.status != "APPROVED" for a in approvals):
        raise HTTPException(status_code=409, detail="All mandatory approval steps must be approved before creating a purchase order")

    existing = db.scalar(select(PurchaseOrder).where(PurchaseOrder.supplier_selection_id == selection.id))
    if existing:
        raise HTTPException(status_code=409, detail=f"A purchase order already exists for this supplier selection ({existing.po_number})")

    quotation = selection.quotation
    if quotation is None:
        raise HTTPException(status_code=409, detail="The selected supplier does not have a quotation")
    if quotation.rfq_id != selection.rfq_id or quotation.rfq_supplier_id != selection.rfq_supplier_id:
        raise HTTPException(status_code=409, detail="Selected quotation does not match the supplier selection")

    vendor = selection.rfq_supplier.vendor
    po_number = f"PO-{datetime.now(timezone.utc).year}-{secrets.token_hex(3).upper()}"
    request_items = list(request.items)
    if quotation.items:
        quote_ids = {q.request_item_id for q in quotation.items}
        if quote_ids != {i.id for i in request_items}:
            raise HTTPException(status_code=409, detail="Selected quotation does not cover all request items")
        po_items = [PurchaseOrderItem(
            name=q.request_item.name, description=q.request_item.description, quantity=q.quantity,
            unit_price=q.unit_price, line_total=q.line_total,
            specifications=q.request_item.specifications, request_item_id=q.request_item_id,
        ) for q in quotation.items]
        if sum((i.line_total for i in po_items), Decimal("0.00")) != quotation.subtotal:
            raise HTTPException(status_code=409, detail="Quotation line totals do not match quotation subtotal")
    else:
        # Historical supplier quotations intentionally retain the one-package representation.
        po_items = [PurchaseOrderItem(
            name=request_items[0].name if len(request_items) == 1 else request.title,
            description=(request_items[0].description if len(request_items) == 1 else f"Historical package quotation for {len(request_items)} requested lines."),
            quantity=quotation.quoted_quantity, unit_price=quotation.unit_price, line_total=quotation.subtotal,
            specifications=request_items[0].specifications if len(request_items) == 1 else {"source": "LEGACY_PACKAGE_QUOTATION", "request_item_count": len(request_items)},
            request_item_id=request_items[0].id if len(request_items) == 1 else None,
        )]
    po = PurchaseOrder(
        po_number=po_number, purchase_request_id=request.id, supplier_selection_id=selection.id,
        vendor_id=vendor.id, currency=quotation.currency, status="DRAFT", required_date=request.required_date,
        subtotal=quotation.subtotal, tax_amount=quotation.tax_amount, total_amount=quotation.total_amount,
        delivery_days=int(quotation.delivery_days), payment_terms_days=payment_terms_days,
        created_by_user_id=actor.id, notes=payload.notes.strip() if payload.notes else None, items=po_items,
    )
    db.add(po)
    db.flush()

    append_request_event(
        request, actor_type="HUMAN", actor_user_id=actor.id, event_type="PURCHASE_ORDER_CREATED",
        from_status=request.status, to_status=request.status,
        details={"po_number": po.po_number, "supplier_selection_id": str(selection.id), "vendor_code": vendor.vendor_code, "total_amount": str(po.total_amount)},
    )
    record_audit_event(
        db, actor_type=ActorType.HUMAN, actor_user_id=actor.id, action="PURCHASE_ORDER_CREATED",
        entity_type="purchase_order", entity_id=str(po.id),
        details={"po_number": po.po_number, "request_number": request.request_number, "supplier_selection_id": str(selection.id), "vendor_code": vendor.vendor_code, "total_amount": str(po.total_amount)},
    )
    db.commit()
    return _detail(_load(db, po.id))
