import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies.auth import require_permissions
from app.core.database import get_db
from app.models.governance import ActorType
from app.models.identity import User
from app.models.procurement import PurchaseRequest, RFQ, RFQSupplier, SupplierQuotation, SupplierSelection
from app.schemas.supplier_selections import SupplierSelectionCreate, SupplierSelectionDetail, SupplierSelectionSummary
from app.services.audit import record_audit_event
from app.services.approval_routing import route_purchase_request_approvals
from app.services.purchase_requests import append_request_event

router = APIRouter(prefix="/supplier-selections", tags=["supplier-selections"])


def _load(db: Session, selection_id: uuid.UUID):
    return db.scalar(
        select(SupplierSelection)
        .options(
            selectinload(SupplierSelection.rfq).selectinload(RFQ.request),
            selectinload(SupplierSelection.rfq_supplier).selectinload(RFQSupplier.vendor),
            selectinload(SupplierSelection.quotation),
        )
        .where(SupplierSelection.id == selection_id)
    )


def _summary(selection: SupplierSelection) -> SupplierSelectionSummary:
    quotation = selection.quotation
    supplier = selection.rfq_supplier.vendor
    request = selection.rfq.request
    return SupplierSelectionSummary(
        id=selection.id,
        rfq_id=selection.rfq_id,
        rfq_number=selection.rfq.rfq_number,
        request_id=request.id,
        request_number=request.request_number,
        request_title=request.title,
        rfq_supplier_id=selection.rfq_supplier_id,
        supplier_id=supplier.id,
        supplier_code=supplier.vendor_code,
        supplier_name=supplier.legal_name,
        quotation_id=selection.quotation_id,
        currency=quotation.currency,
        quoted_quantity=quotation.quoted_quantity,
        unit_price=quotation.unit_price,
        subtotal=quotation.subtotal,
        tax_amount=quotation.tax_amount,
        total_amount=quotation.total_amount,
        delivery_days=int(quotation.delivery_days),
        valid_until=quotation.valid_until,
        rationale=selection.rationale,
        selected_at=selection.selected_at,
        selected_by_user_id=selection.selected_by_user_id,
    )


def _detail(selection: SupplierSelection) -> SupplierSelectionDetail:
    return SupplierSelectionDetail(**_summary(selection).model_dump())


@router.get("", response_model=list[SupplierSelectionSummary])
def list_supplier_selections(
    actor: User = Depends(require_permissions("sourcing.manage")),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(SupplierSelection)
        .options(
            selectinload(SupplierSelection.rfq).selectinload(RFQ.request),
            selectinload(SupplierSelection.rfq_supplier).selectinload(RFQSupplier.vendor),
            selectinload(SupplierSelection.quotation),
        )
        .order_by(SupplierSelection.selected_at.desc())
    ).all()
    return [_summary(row) for row in rows]


@router.get("/rfq/{rfq_id}", response_model=SupplierSelectionSummary)
def get_supplier_selection_for_rfq(
    rfq_id: uuid.UUID,
    actor: User = Depends(require_permissions("sourcing.manage")),
    db: Session = Depends(get_db),
):
    selection = db.scalar(
        select(SupplierSelection)
        .options(
            selectinload(SupplierSelection.rfq).selectinload(RFQ.request),
            selectinload(SupplierSelection.rfq_supplier).selectinload(RFQSupplier.vendor),
            selectinload(SupplierSelection.quotation),
        )
        .where(SupplierSelection.rfq_id == rfq_id)
    )
    if not selection:
        raise HTTPException(status_code=404, detail="No supplier has been selected for this RFQ")
    return _summary(selection)


@router.post("", response_model=SupplierSelectionDetail, status_code=status.HTTP_201_CREATED)
def select_supplier(
    payload: SupplierSelectionCreate,
    actor: User = Depends(require_permissions("sourcing.manage")),
    db: Session = Depends(get_db),
):
    rationale = payload.rationale.strip()
    if len(rationale) < 10:
        raise HTTPException(status_code=422, detail="Selection rationale must be at least 10 characters")

    rfq = db.scalar(
        select(RFQ)
        .options(selectinload(RFQ.request))
        .where(RFQ.id == payload.rfq_id)
    )
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    if rfq.status != "SENT":
        raise HTTPException(status_code=409, detail=f"Supplier selection is available only for sent RFQs (current status: {rfq.status})")
    if rfq.request.status != "SOURCING":
        raise HTTPException(status_code=409, detail=f"Purchase request cannot complete sourcing from status {rfq.request.status}")

    existing = db.scalar(select(SupplierSelection).where(SupplierSelection.rfq_id == rfq.id))
    if existing:
        raise HTTPException(status_code=409, detail="A supplier has already been selected for this RFQ")

    invitation = db.scalar(
        select(RFQSupplier)
        .options(selectinload(RFQSupplier.vendor), selectinload(RFQSupplier.quotation))
        .where(RFQSupplier.id == payload.rfq_supplier_id, RFQSupplier.rfq_id == rfq.id)
    )
    if not invitation:
        raise HTTPException(status_code=404, detail="Supplier invitation not found for this RFQ")
    # A supplier invitation starts as SENT and moves to RESPONDED after the
    # supplier submits a quotation through the secure response portal.
    # Keep SENT accepted for backwards compatibility with quotations recorded
    # through the legacy internal workflow; the quotation-presence check below
    # still prevents selection without an actual quotation.
    if invitation.status not in {"SENT", "RESPONDED"}:
        raise HTTPException(status_code=409, detail="The selected supplier invitation is not ready for supplier selection")
    if invitation.quotation is None:
        raise HTTPException(status_code=409, detail="A supplier must have a recorded quotation before selection")

    quotation = invitation.quotation
    selection = SupplierSelection(
        rfq_id=rfq.id,
        rfq_supplier_id=invitation.id,
        quotation_id=quotation.id,
        rationale=rationale,
        selected_at=datetime.now(timezone.utc),
        selected_by_user_id=actor.id,
    )
    db.add(selection)
    db.flush()

    previous_status = rfq.request.status
    rfq.request.status = "SUPPLIER_SELECTED"
    append_request_event(
        rfq.request,
        actor_type="HUMAN",
        actor_user_id=actor.id,
        event_type="SUPPLIER_SELECTED",
        from_status=previous_status,
        to_status="SUPPLIER_SELECTED",
        details={
            "rfq_number": rfq.rfq_number,
            "supplier_code": invitation.vendor.vendor_code,
            "supplier_name": invitation.vendor.legal_name,
            "quotation_id": str(quotation.id),
            "quotation_total": str(quotation.total_amount),
            "quotation_tax": str(quotation.tax_amount),
            "selection_id": str(selection.id),
            "rationale": rationale,
        },
    )
    record_audit_event(
        db,
        actor_type=ActorType.HUMAN,
        actor_user_id=actor.id,
        action="SUPPLIER_SELECTED",
        entity_type="supplier_selection",
        entity_id=str(selection.id),
        details={
            "rfq_number": rfq.rfq_number,
            "request_number": rfq.request.request_number,
            "supplier_code": invitation.vendor.vendor_code,
            "supplier_name": invitation.vendor.legal_name,
            "quotation_id": str(quotation.id),
            "total_amount": str(quotation.total_amount),
        },
    )
    try:
        approvals = route_purchase_request_approvals(db, rfq.request)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    approval_details = [{"sequence": a.sequence, "approver_user_id": str(a.approver_user_id), "approver_role": a.approver_role, "status": a.status} for a in approvals]
    append_request_event(rfq.request, actor_type="SYSTEM", event_type="APPROVALS_ROUTED", from_status="SUPPLIER_SELECTED", to_status="PENDING_APPROVAL", details={"approval_chain": approval_details})
    record_audit_event(db, actor_type=ActorType.SYSTEM, action="APPROVAL_CREATED", entity_type="purchase_request", entity_id=str(rfq.request.id), details={"approval_chain": approval_details})
    db.commit()
    return _detail(_load(db, selection.id))


@router.get("/{selection_id}", response_model=SupplierSelectionDetail)
def get_supplier_selection(
    selection_id: uuid.UUID,
    actor: User = Depends(require_permissions("sourcing.manage")),
    db: Session = Depends(get_db),
):
    selection = _load(db, selection_id)
    if not selection:
        raise HTTPException(status_code=404, detail="Supplier selection not found")
    return _detail(selection)
