import uuid
from decimal import Decimal
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies.auth import require_any_permissions, require_permissions
from app.core.config import settings
from app.core.database import get_db
from app.models.governance import ActorType
from app.models.goods_receipts import GoodsReceipt, GoodsReceiptItem
from app.models.identity import User
from app.models.invoice_matching import SupplierInvoiceMatch
from app.models.invoices import SupplierInvoice, SupplierInvoiceItem
from app.models.procurement import PurchaseOrder, PurchaseOrderItem
from app.schemas.invoice_matching import InvoiceMatchLine, InvoiceMatchResponse, InvoiceMatchingQueueItem
from app.services.audit import record_audit_event
from app.services.purchase_requests import append_request_event

router = APIRouter(prefix="/invoice-matching", tags=["invoice-matching"])


def _money(value: Decimal | None) -> Decimal:
    return Decimal(value or 0).quantize(Decimal("0.01"))


def _load_invoice(db: Session, invoice_id: uuid.UUID) -> SupplierInvoice | None:
    return db.scalar(
        select(SupplierInvoice)
        .options(
            selectinload(SupplierInvoice.vendor),
            selectinload(SupplierInvoice.purchase_order).selectinload(PurchaseOrder.items),
            selectinload(SupplierInvoice.purchase_order).selectinload(PurchaseOrder.request),
            selectinload(SupplierInvoice.items).selectinload(SupplierInvoiceItem.purchase_order_item),
        )
        .where(SupplierInvoice.id == invoice_id)
    )


def _posted_receipts(db: Session, po_id: uuid.UUID) -> dict[uuid.UUID, tuple[Decimal, Decimal]]:
    rows = db.execute(
        select(
            GoodsReceiptItem.purchase_order_item_id,
            func.coalesce(func.sum(GoodsReceiptItem.received_quantity), 0),
            func.coalesce(func.sum(GoodsReceiptItem.accepted_quantity), 0),
        )
        .join(GoodsReceipt, GoodsReceipt.id == GoodsReceiptItem.goods_receipt_id)
        .where(GoodsReceipt.purchase_order_id == po_id, GoodsReceipt.status == "POSTED")
        .group_by(GoodsReceiptItem.purchase_order_item_id)
    ).all()
    return {row[0]: (Decimal(row[1] or 0), Decimal(row[2] or 0)) for row in rows}


def _latest_match(db: Session, invoice_id: uuid.UUID) -> SupplierInvoiceMatch | None:
    return db.scalar(
        select(SupplierInvoiceMatch)
        .where(SupplierInvoiceMatch.invoice_id == invoice_id)
        .order_by(SupplierInvoiceMatch.evaluated_at.desc())
    )


def _response(match: SupplierInvoiceMatch) -> InvoiceMatchResponse:
    invoice = match.invoice
    po = match.purchase_order
    lines = [InvoiceMatchLine(**line) for line in (match.line_results or [])]
    return InvoiceMatchResponse(
        id=match.id, invoice_id=match.invoice_id, invoice_number=invoice.invoice_number,
        purchase_order_id=match.purchase_order_id, po_number=po.po_number,
        supplier_name=invoice.vendor.legal_name, currency=invoice.currency, result=match.result,
        po_quantity=match.po_quantity, received_quantity=match.received_quantity,
        accepted_quantity=match.accepted_quantity, invoice_quantity=match.invoice_quantity,
        quantity_variance=match.quantity_variance, po_amount=match.po_amount,
        invoice_amount=match.invoice_amount, price_variance=match.price_variance,
        price_variance_percent=match.price_variance_percent,
        quantity_tolerance=match.quantity_tolerance,
        price_tolerance_percent=match.price_tolerance_percent,
        exception_reason=match.exception_reason, line_results=lines,
        evaluated_by_user_id=match.evaluated_by_user_id, evaluated_at=match.evaluated_at,
    )


def _evaluate(db: Session, invoice: SupplierInvoice, actor: User) -> SupplierInvoiceMatch:
    po = invoice.purchase_order
    receipts = _posted_receipts(db, po.id)
    po_items = {item.id: item for item in po.items}
    invoice_items = {item.purchase_order_item_id: item for item in invoice.items}

    quantity_tolerance = Decimal(settings.match_quantity_tolerance).quantize(Decimal("0.01"))
    price_tolerance_percent = Decimal(settings.match_price_tolerance_percent).quantize(Decimal("0.0001"))
    po_quantity = Decimal("0")
    received_quantity = Decimal("0")
    accepted_quantity = Decimal("0")
    invoice_quantity = Decimal("0")
    po_amount = Decimal("0")
    invoice_amount = Decimal("0")
    line_results: list[dict] = []
    failures: list[str] = []

    for po_item in po.items:
        po_qty = Decimal(po_item.quantity)
        po_quantity += po_qty
        po_amount += Decimal(po_item.line_total)
        received, accepted = receipts.get(po_item.id, (Decimal("0"), Decimal("0")))
        received_quantity += received
        accepted_quantity += accepted
        invoice_item = invoice_items.get(po_item.id)
        inv_qty = Decimal(invoice_item.quantity) if invoice_item else Decimal("0")
        inv_price = Decimal(invoice_item.unit_price) if invoice_item else Decimal("0")
        invoice_quantity += inv_qty
        if invoice_item:
            invoice_amount += Decimal(invoice_item.line_total)
        qty_variance = inv_qty - po_qty
        receipt_variance = inv_qty - accepted
        price_variance = inv_price - Decimal(po_item.unit_price)
        price_pass = abs(price_variance) <= (Decimal(po_item.unit_price) * price_tolerance_percent / Decimal("100"))
        quantity_pass = abs(qty_variance) <= quantity_tolerance
        receipt_pass = abs(receipt_variance) <= quantity_tolerance
        if not quantity_pass:
            failures.append(f"{po_item.name}: invoice quantity differs from PO by {qty_variance}.")
        if not receipt_pass:
            failures.append(f"{po_item.name}: invoice quantity differs from accepted receipt quantity by {receipt_variance}.")
        if not price_pass:
            failures.append(f"{po_item.name}: invoice unit price differs from PO by {price_variance}.")
        line_results.append({
            "purchase_order_item_id": str(po_item.id), "description": po_item.name,
            "po_quantity": str(po_qty), "received_quantity": str(received), "accepted_quantity": str(accepted),
            "invoice_quantity": str(inv_qty), "po_unit_price": str(Decimal(po_item.unit_price)),
            "invoice_unit_price": str(inv_price), "quantity_variance": str(qty_variance),
            "price_variance": str(price_variance), "quantity_pass": quantity_pass,
            "price_pass": price_pass, "receipt_pass": receipt_pass,
        })

    extra_invoice_lines = set(invoice_items) - set(po_items)
    if extra_invoice_lines:
        failures.append("Invoice contains a line that is not present on the purchase order.")

    price_variance = invoice_amount - po_amount
    price_variance_percent = (abs(price_variance) / po_amount * Decimal("100")) if po_amount else (Decimal("0") if invoice_amount == 0 else Decimal("100"))
    price_variance_percent = price_variance_percent.quantize(Decimal("0.0001"))
    result = "MATCHED" if not failures else "EXCEPTION"
    reason = None if not failures else " ".join(failures)[:1000]

    match = SupplierInvoiceMatch(
        invoice_id=invoice.id, purchase_order_id=po.id, result=result,
        po_quantity=po_quantity, received_quantity=received_quantity, accepted_quantity=accepted_quantity,
        invoice_quantity=invoice_quantity, quantity_variance=invoice_quantity - accepted_quantity,
        po_amount=po_amount, invoice_amount=invoice_amount, price_variance=price_variance,
        price_variance_percent=price_variance_percent, quantity_tolerance=quantity_tolerance,
        price_tolerance_percent=price_tolerance_percent, exception_reason=reason,
        line_results=line_results, evaluated_by_user_id=actor.id,
    )
    return match


@router.get("", response_model=list[InvoiceMatchingQueueItem])
def matching_queue(
    actor: User = Depends(require_any_permissions("invoices.review", "finance.review")),
    db: Session = Depends(get_db),
):
    invoices = db.scalars(
        select(SupplierInvoice)
        .options(selectinload(SupplierInvoice.vendor), selectinload(SupplierInvoice.purchase_order))
        .where(SupplierInvoice.status == "MATCHING")
        .order_by(SupplierInvoice.created_at.desc())
    ).all()
    return [InvoiceMatchingQueueItem(
        invoice_id=i.id, invoice_number=i.invoice_number, purchase_order_id=i.purchase_order_id,
        po_number=i.purchase_order.po_number, supplier_name=i.vendor.legal_name, currency=i.currency,
        total_amount=i.total_amount, invoice_date=i.invoice_date, status=i.status,
    ) for i in invoices]


@router.get("/payment-queue", response_model=list[dict])
def payment_queue(
    actor: User = Depends(require_permissions("finance.review")),
    db: Session = Depends(get_db),
):
    invoices = db.scalars(
        select(SupplierInvoice)
        .options(selectinload(SupplierInvoice.vendor), selectinload(SupplierInvoice.purchase_order))
        .where(SupplierInvoice.status.in_(["READY_FOR_PAYMENT", "PAID"]))
        .order_by(SupplierInvoice.due_date.asc(), SupplierInvoice.created_at.desc())
    ).all()
    return [{
        "id": i.id, "invoice_number": i.invoice_number, "po_number": i.purchase_order.po_number,
        "supplier_name": i.vendor.legal_name, "currency": i.currency, "total_amount": i.total_amount,
        "invoice_date": i.invoice_date, "due_date": i.due_date, "status": i.status,
        "payment_reference": i.payment_reference, "paid_at": i.paid_at,
    } for i in invoices]


@router.get("/{invoice_id}", response_model=InvoiceMatchResponse | None)
def get_matching_result(
    invoice_id: uuid.UUID,
    actor: User = Depends(require_any_permissions("invoices.review", "finance.review")),
    db: Session = Depends(get_db),
):
    match = _latest_match(db, invoice_id)
    return _response(match) if match else None


@router.post("/{invoice_id}/finalize-payment", response_model=dict)
def finalize_payment(
    invoice_id: uuid.UUID,
    actor: User = Depends(require_permissions("finance.review")),
    db: Session = Depends(get_db),
):
    invoice = _load_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status != "READY_FOR_PAYMENT":
        raise HTTPException(status_code=409, detail=f"Only invoices cleared by 3-way matching can be finalized (current status: {invoice.status}).")
    match = _latest_match(db, invoice.id)
    if not match or match.result != "MATCHED":
        raise HTTPException(status_code=409, detail="A successful 3-way match is required before payment finalization.")
    paid_at = datetime.now(timezone.utc)
    payment_reference = f"PAY-{paid_at.strftime('%Y')}-{uuid.uuid4().hex[:8].upper()}"
    invoice.payment_reference = payment_reference
    invoice.paid_at = paid_at
    invoice.paid_by_user_id = actor.id
    invoice.status = "PAID"
    record_audit_event(
        db, actor_type=ActorType.HUMAN, actor_user_id=actor.id, action="SUPPLIER_INVOICE_PAYMENT_FINALIZED",
        entity_type="supplier_invoice", entity_id=str(invoice.id),
        details={"invoice_number": invoice.invoice_number, "po_number": invoice.purchase_order.po_number,
                 "amount": str(invoice.total_amount), "currency": invoice.currency,
                 "payment_reference": payment_reference},
    )
    request = invoice.purchase_order.request
    append_request_event(request, actor_type="HUMAN", actor_user_id=actor.id,
        event_type="PAYMENT_FINALIZED", details={"invoice_number": invoice.invoice_number,
        "po_number": invoice.purchase_order.po_number, "payment_reference": payment_reference,
        "total_amount": str(invoice.total_amount)})
    db.commit()
    return {"id": invoice.id, "invoice_number": invoice.invoice_number, "status": invoice.status,
            "payment_reference": payment_reference, "paid_at": invoice.paid_at}


@router.post("/{invoice_id}/run", response_model=InvoiceMatchResponse)
def run_three_way_match(
    invoice_id: uuid.UUID,
    actor: User = Depends(require_permissions("invoices.review")),
    db: Session = Depends(get_db),
):
    invoice = _load_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status != "MATCHING":
        raise HTTPException(status_code=409, detail=f"Only invoices in MATCHING can be evaluated (current status: {invoice.status}).")

    match = _evaluate(db, invoice, actor)
    existing = _latest_match(db, invoice.id)
    if existing:
        for key, value in {
            "purchase_order_id": match.purchase_order_id, "result": match.result,
            "po_quantity": match.po_quantity, "received_quantity": match.received_quantity,
            "accepted_quantity": match.accepted_quantity, "invoice_quantity": match.invoice_quantity,
            "quantity_variance": match.quantity_variance, "po_amount": match.po_amount,
            "invoice_amount": match.invoice_amount, "price_variance": match.price_variance,
            "price_variance_percent": match.price_variance_percent,
            "quantity_tolerance": match.quantity_tolerance,
            "price_tolerance_percent": match.price_tolerance_percent,
            "exception_reason": match.exception_reason, "line_results": match.line_results,
            "evaluated_by_user_id": match.evaluated_by_user_id,
            "evaluated_at": datetime.now(timezone.utc),
        }.items():
            setattr(existing, key, value)
        match = existing
    else:
        db.add(match)
    invoice.status = "READY_FOR_PAYMENT" if match.result == "MATCHED" else "EXCEPTION"
    record_audit_event(
        db, actor_type=ActorType.HUMAN, actor_user_id=actor.id,
        action="SUPPLIER_INVOICE_MATCHED" if match.result == "MATCHED" else "SUPPLIER_INVOICE_MATCH_EXCEPTION",
        entity_type="supplier_invoice", entity_id=str(invoice.id),
        details={
            "invoice_number": invoice.invoice_number, "po_number": invoice.purchase_order.po_number,
            "result": match.result, "quantity_variance": str(match.quantity_variance),
            "price_variance": str(match.price_variance), "price_variance_percent": str(match.price_variance_percent),
        },
    )
    db.commit()
    db.refresh(match)
    return _response(match)
