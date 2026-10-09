import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies.auth import require_permissions
from app.core.database import get_db
from app.core.config import settings
from app.models.governance import ActorType
from app.models.identity import User, Vendor
from app.models.procurement import PurchaseRequest, PurchaseRequestItem, RequestEvent, RFQ, RFQSupplier
from app.schemas.rfqs import RFQCreate, RFQDetail, RFQSummary, RFQSupplierResponse
from app.services.audit import record_audit_event
from app.services.purchase_requests import append_request_event
from app.services.supplier_email import build_rfq_email, send_email

router = APIRouter(prefix="/rfqs", tags=["rfqs"])

def _number():
    now = datetime.now(timezone.utc)
    return f"RFQ-{now.year}-{uuid.uuid4().hex[:6].upper()}"

def _load(db, rfq_id):
    return db.scalar(select(RFQ).options(selectinload(RFQ.suppliers).selectinload(RFQSupplier.vendor)).where(RFQ.id == rfq_id))

def _summary(r):
    return RFQSummary(id=r.id, rfq_number=r.rfq_number, request_id=r.request_id, request_number=r.request.request_number, request_title=r.request.title, status=r.status, response_deadline=r.response_deadline, supplier_count=len(r.suppliers), sent_at=r.sent_at, created_at=r.created_at, updated_at=r.updated_at)

def _detail(r):
    return RFQDetail(**_summary(r).model_dump(), instructions=r.instructions, suppliers=[RFQSupplierResponse(id=x.id, vendor_id=x.vendor_id, vendor_code=x.vendor.vendor_code, vendor_name=x.vendor.legal_name, email=x.vendor.email, status=x.status, sent_at=x.sent_at) for x in r.suppliers])

@router.get("/eligible-suppliers")
def eligible_suppliers(actor: User = Depends(require_permissions("sourcing.manage")), db: Session = Depends(get_db)):
    vendors = db.scalars(select(Vendor).where(Vendor.is_active.is_(True)).order_by(Vendor.vendor_code)).all()
    return [{"id": v.id, "vendor_code": v.vendor_code, "legal_name": v.legal_name, "email": v.email, "capabilities": v.capabilities} for v in vendors]

@router.get("", response_model=list[RFQSummary])
def list_rfqs(actor: User = Depends(require_permissions("sourcing.manage")), db: Session = Depends(get_db)):
    rows = db.scalars(select(RFQ).options(selectinload(RFQ.request), selectinload(RFQ.suppliers)).order_by(RFQ.created_at.desc())).all()
    return [_summary(r) for r in rows]

@router.post("", response_model=RFQDetail, status_code=status.HTTP_201_CREATED)
def create_rfq(payload: RFQCreate, actor: User = Depends(require_permissions("sourcing.manage")), db: Session = Depends(get_db)):
    request = db.scalar(select(PurchaseRequest).where(PurchaseRequest.id == payload.request_id))
    if not request:
        raise HTTPException(status_code=404, detail="Purchase request not found")
    if request.status != "SOURCING":
        raise HTTPException(status_code=409, detail="Start sourcing on the purchase request before creating an RFQ")
    if payload.response_deadline <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Response deadline must be in the future")
    vendors = db.scalars(select(Vendor).where(Vendor.id.in_(payload.vendor_ids), Vendor.is_active.is_(True))).all()
    if len(vendors) != len(payload.vendor_ids):
        raise HTTPException(status_code=422, detail="One or more selected suppliers are unavailable or inactive")
    rfq = RFQ(rfq_number=_number(), request_id=request.id, status="DRAFT", response_deadline=payload.response_deadline, instructions=payload.instructions.strip() if payload.instructions else None, created_by_user_id=actor.id)
    rfq.suppliers = [RFQSupplier(vendor_id=v.id, status="INVITED") for v in vendors]
    db.add(rfq); db.flush()
    record_audit_event(db, actor_type=ActorType.HUMAN, actor_user_id=actor.id, action="RFQ_CREATED", entity_type="rfq", entity_id=str(rfq.id), details={"rfq_number": rfq.rfq_number, "request_number": request.request_number, "supplier_count": len(vendors)})
    db.commit()
    return _detail(_load(db, rfq.id))

@router.post("/{rfq_id}/send", response_model=RFQDetail)
def send_rfq(rfq_id: uuid.UUID, actor: User = Depends(require_permissions("sourcing.manage")), db: Session = Depends(get_db)):
    rfq = _load(db, rfq_id)
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    if rfq.status != "DRAFT":
        raise HTTPException(status_code=409, detail=f"RFQ cannot be sent from status {rfq.status}")
    if rfq.response_deadline <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="Response deadline has passed. Update the RFQ before sending")
    if not rfq.suppliers:
        raise HTTPException(status_code=409, detail="RFQ has no supplier invitations")

    items = db.scalars(select(PurchaseRequestItem).where(PurchaseRequestItem.request_id == rfq.request_id)).all()
    item_lines = [
        f"{item.name} — quantity {item.quantity}" + (f" — {item.description}" if item.description else "")
        for item in items
    ]
    now = datetime.now(timezone.utc)
    recipients = []
    for supplier in rfq.suppliers:
        raw_token = secrets.token_urlsafe(32)
        supplier.response_token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        supplier.response_token_expires_at = rfq.response_deadline
        response_url = f"{settings.public_base_url.rstrip('/')}/api/v1/supplier-responses/{raw_token}"
        message = build_rfq_email(
            to_email=supplier.vendor.email,
            supplier_name=supplier.vendor.contact_person or supplier.vendor.legal_name,
            rfq_number=rfq.rfq_number,
            request_title=rfq.request.title,
            response_deadline=rfq.response_deadline.strftime("%d %b %Y, %H:%M UTC"),
            response_url=response_url,
            item_lines=item_lines or ["Requested goods/services — see RFQ instructions"],
            instructions=rfq.instructions,
        )
        try:
            send_email(message)
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=502, detail=f"RFQ email could not be sent to {supplier.vendor.email}: {exc}") from exc
        supplier.status = "SENT"
        supplier.sent_at = now
        recipients.append(supplier.vendor.email)

    rfq.status = "SENT"
    rfq.sent_at = now
    append_request_event(rfq.request, actor_type="HUMAN", actor_user_id=actor.id, event_type="RFQ_SENT", details={"rfq_number": rfq.rfq_number, "supplier_count": len(rfq.suppliers), "delivery": "EMAIL"})
    record_audit_event(db, actor_type=ActorType.HUMAN, actor_user_id=actor.id, action="RFQ_SENT", entity_type="rfq", entity_id=str(rfq.id), details={"rfq_number": rfq.rfq_number, "supplier_count": len(rfq.suppliers), "delivery": "EMAIL", "recipients": recipients})
    db.commit()
    return _detail(_load(db, rfq.id))

@router.get("/{rfq_id}", response_model=RFQDetail)
def get_rfq(rfq_id: uuid.UUID, actor: User = Depends(require_permissions("sourcing.manage")), db: Session = Depends(get_db)):
    rfq = _load(db, rfq_id)
    if not rfq: raise HTTPException(status_code=404, detail="RFQ not found")
    return _detail(rfq)
