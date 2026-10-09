import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies.auth import require_permissions
from app.core.database import get_db
from app.models.governance import ActorType
from app.models.identity import User
from app.models.procurement import PurchaseRequest, PurchaseRequestItem, RFQ, RFQSupplier, SupplierQuotation, SupplierQuotationItem
from app.schemas.quotations import (
    PendingQuotationTarget,
    QuotationCreate,
    QuotationComparison,
    QuotationComparisonRow,
    QuotationDetail,
    QuotationSummary,
)
from app.services.audit import record_audit_event
from app.services.quotation_lines import normalized_lines
from app.schemas.quotations import QuotationLineResponse
from app.services.purchase_requests import append_request_event

router = APIRouter(prefix="/quotations", tags=["quotations"])


def _load(db: Session, quotation_id: uuid.UUID):
    return db.scalar(
        select(SupplierQuotation)
        .options(
            selectinload(SupplierQuotation.rfq).selectinload(RFQ.request),
            selectinload(SupplierQuotation.rfq_supplier).selectinload(RFQSupplier.vendor),
            selectinload(SupplierQuotation.items).selectinload(SupplierQuotationItem.request_item),
        )
        .where(SupplierQuotation.id == quotation_id)
    )


def _summary(q):
    supplier = q.rfq_supplier.vendor
    return QuotationSummary(
        id=q.id,
        rfq_id=q.rfq_id,
        rfq_number=q.rfq.rfq_number,
        request_number=q.rfq.request.request_number,
        request_title=q.rfq.request.title,
        request_status=q.rfq.request.status,
        rfq_supplier_id=q.rfq_supplier_id,
        vendor_id=supplier.id,
        vendor_code=supplier.vendor_code,
        vendor_name=supplier.legal_name,
        currency=q.currency,
        quoted_quantity=q.quoted_quantity,
        unit_price=q.unit_price,
        subtotal=q.subtotal,
        tax_amount=q.tax_amount,
        total_amount=q.total_amount,
        delivery_days=int(q.delivery_days),
        valid_until=q.valid_until,
        status=q.status,
        received_at=q.received_at,
        notes=q.notes,
        created_at=q.created_at,
        updated_at=q.updated_at,
        items=[QuotationLineResponse(request_item_id=i.request_item_id, item_name=i.request_item.name, quantity=i.quantity, unit_price=i.unit_price, line_total=i.line_total) for i in q.items],
    )


def _detail(q):
    return QuotationDetail(**_summary(q).model_dump(), recorded_by_user_id=q.recorded_by_user_id)


@router.get("", response_model=list[QuotationSummary])
def list_quotations(
    actor: User = Depends(require_permissions("sourcing.manage")),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(SupplierQuotation)
        .options(
            selectinload(SupplierQuotation.rfq).selectinload(RFQ.request),
            selectinload(SupplierQuotation.rfq_supplier).selectinload(RFQSupplier.vendor),
            selectinload(SupplierQuotation.items).selectinload(SupplierQuotationItem.request_item),
        )
        .order_by(SupplierQuotation.received_at.desc())
    ).all()
    return [_summary(q) for q in rows]


@router.get("/pending", response_model=list[PendingQuotationTarget])
def pending_quotations(
    actor: User = Depends(require_permissions("sourcing.manage")),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(RFQSupplier)
        .join(RFQ, RFQ.id == RFQSupplier.rfq_id)
        .options(
            selectinload(RFQSupplier.rfq).selectinload(RFQ.request).selectinload(PurchaseRequest.items),
            selectinload(RFQSupplier.vendor),
            selectinload(RFQSupplier.quotation),
        )
        .where(RFQ.status == "SENT", RFQSupplier.status == "SENT")
        .order_by(RFQ.response_deadline.asc(), RFQSupplier.created_at.asc())
    ).all()

    pending = []
    for row in rows:
        if row.quotation is not None:
            continue
        request = row.rfq.request
        first_item = request.items[0] if request.items else None
        pending.append(
            PendingQuotationTarget(
                rfq_supplier_id=row.id,
                rfq_id=row.rfq.id,
                rfq_number=row.rfq.rfq_number,
                request_number=request.request_number,
                request_title=request.title,
                request_status=request.status,
                supplier_id=row.vendor.id,
                supplier_code=row.vendor.vendor_code,
                supplier_name=row.vendor.legal_name,
                supplier_email=row.vendor.email,
                currency=request.currency or "INR",
                item_name=first_item.name if first_item else "Requested goods/services",
                quantity=first_item.quantity if first_item else Decimal("1"),
                response_deadline=row.rfq.response_deadline,
            )
        )
    return pending


@router.post("", response_model=QuotationDetail, status_code=status.HTTP_201_CREATED)
def record_quotation(
    payload: QuotationCreate,
    actor: User = Depends(require_permissions("sourcing.manage")),
    db: Session = Depends(get_db),
):
    rfq = db.scalar(select(RFQ).options(selectinload(RFQ.request).selectinload(PurchaseRequest.items)).where(RFQ.id == payload.rfq_id))
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    if rfq.status != "SENT":
        raise HTTPException(status_code=409, detail="Supplier quotations can only be recorded for a sent RFQ")

    rfq_supplier = db.scalar(
        select(RFQSupplier)
        .options(selectinload(RFQSupplier.vendor), selectinload(RFQSupplier.quotation))
        .where(RFQSupplier.id == payload.rfq_supplier_id, RFQSupplier.rfq_id == payload.rfq_id)
    )
    if not rfq_supplier:
        raise HTTPException(status_code=404, detail="Supplier invitation not found for this RFQ")
    if rfq_supplier.status != "SENT":
        raise HTTPException(status_code=409, detail="This supplier invitation is not in a response-ready state")
    if rfq_supplier.quotation is not None:
        raise HTTPException(status_code=409, detail="A quotation has already been recorded for this supplier")

    currency = payload.currency.strip().upper()
    expected_currency = rfq.request.currency or "INR"
    if currency != expected_currency:
        raise HTTPException(status_code=422, detail=f"Quotation currency must match the request currency ({expected_currency})")

    if len(rfq.request.items) > 1 and not payload.items:
        raise HTTPException(status_code=422, detail="Itemized supplier prices are required for multi-item requests.")
    try:
        lines = normalized_lines(rfq.request.items, payload.items) if payload.items else []
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    subtotal = sum((line[3] for line in lines), Decimal("0.00")) if lines else (payload.quoted_quantity * payload.unit_price).quantize(Decimal("0.01"))
    total = (subtotal + payload.tax_amount).quantize(Decimal("0.01"))

    quotation = SupplierQuotation(
        rfq_id=rfq.id,
        rfq_supplier_id=rfq_supplier.id,
        currency=currency,
        quoted_quantity=Decimal("1") if lines else payload.quoted_quantity,
        unit_price=subtotal if lines else payload.unit_price,
        subtotal=subtotal,
        tax_amount=payload.tax_amount,
        total_amount=total,
        delivery_days=payload.delivery_days,
        valid_until=payload.valid_until,
        notes=payload.notes.strip() if payload.notes else None,
        status="RECEIVED",
        received_at=datetime.now(timezone.utc),
        recorded_by_user_id=actor.id,
    )
    db.add(quotation)
    db.flush()
    for item, qty, price, amount in lines:
        quotation.items.append(SupplierQuotationItem(request_item_id=item.id, quantity=qty, unit_price=price, line_total=amount))

    append_request_event(
        rfq.request,
        actor_type="HUMAN",
        actor_user_id=actor.id,
        event_type="QUOTATION_RECEIVED",
        details={
            "rfq_number": rfq.rfq_number,
            "supplier_code": rfq_supplier.vendor.vendor_code,
            "supplier_name": rfq_supplier.vendor.legal_name,
            "quotation_id": str(quotation.id),
            "total_amount": str(total),
        },
    )
    record_audit_event(
        db,
        actor_type=ActorType.HUMAN,
        actor_user_id=actor.id,
        action="QUOTATION_RECORDED",
        entity_type="supplier_quotation",
        entity_id=str(quotation.id),
        details={
            "rfq_number": rfq.rfq_number,
            "supplier_code": rfq_supplier.vendor.vendor_code,
            "supplier_name": rfq_supplier.vendor.legal_name,
            "total_amount": str(total),
        },
    )
    db.commit()
    return _detail(_load(db, quotation.id))


@router.get("/compare/{rfq_id}", response_model=QuotationComparison)
def compare_quotations(
    rfq_id: uuid.UUID,
    actor: User = Depends(require_permissions("sourcing.manage")),
    db: Session = Depends(get_db),
):
    rfq = db.scalar(
        select(RFQ)
        .options(
            selectinload(RFQ.request),
            selectinload(RFQ.suppliers).selectinload(RFQSupplier.vendor),
            selectinload(RFQ.suppliers).selectinload(RFQSupplier.quotation).selectinload(SupplierQuotation.items).selectinload(SupplierQuotationItem.request_item),
        )
        .where(RFQ.id == rfq_id)
    )
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    if rfq.status != "SENT":
        raise HTTPException(status_code=409, detail="Quotation comparison is available only for sent RFQs")

    rows = []
    for invitation in rfq.suppliers:
        quotation = invitation.quotation
        rows.append(
            QuotationComparisonRow(
                rfq_supplier_id=invitation.id,
                supplier_id=invitation.vendor.id,
                supplier_code=invitation.vendor.vendor_code,
                supplier_name=invitation.vendor.legal_name,
                supplier_email=invitation.vendor.email,
                invitation_status=invitation.status,
                quotation_id=quotation.id if quotation else None,
                quotation_status=quotation.status if quotation else None,
                currency=quotation.currency if quotation else (rfq.request.currency or "INR"),
                quoted_quantity=quotation.quoted_quantity if quotation else None,
                unit_price=quotation.unit_price if quotation else None,
                subtotal=quotation.subtotal if quotation else None,
                tax_amount=quotation.tax_amount if quotation else None,
                total_amount=quotation.total_amount if quotation else None,
                delivery_days=int(quotation.delivery_days) if quotation else None,
                valid_until=quotation.valid_until if quotation else None,
                received_at=quotation.received_at if quotation else None,
                notes=quotation.notes if quotation else None,
                items=[QuotationLineResponse(request_item_id=i.request_item_id, item_name=i.request_item.name, quantity=i.quantity, unit_price=i.unit_price, line_total=i.line_total) for i in quotation.items] if quotation else [],
            )
        )

    received = sum(1 for row in rows if row.quotation_id is not None)
    return QuotationComparison(
        rfq_id=rfq.id,
        rfq_number=rfq.rfq_number,
        request_id=rfq.request.id,
        request_number=rfq.request.request_number,
        request_title=rfq.request.title,
        request_status=rfq.request.status,
        request_category=rfq.request.category,
        request_currency=rfq.request.currency or "INR",
        response_deadline=rfq.response_deadline,
        invited_supplier_count=len(rows),
        received_quotation_count=received,
        pending_response_count=len(rows) - received,
        rows=rows,
    )


@router.get("/{quotation_id}", response_model=QuotationDetail)
def get_quotation(
    quotation_id: uuid.UUID,
    actor: User = Depends(require_permissions("sourcing.manage")),
    db: Session = Depends(get_db),
):
    quotation = _load(db, quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    return _detail(quotation)
