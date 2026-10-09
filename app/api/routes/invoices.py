import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies.auth import require_any_permissions, require_permissions
from app.core.database import get_db
from app.models.governance import ActorType
from app.models.identity import User
from app.models.invoices import SupplierInvoice, SupplierInvoiceItem
from app.models.procurement import PurchaseOrder, PurchaseOrderItem
from app.services.audit import record_audit_event
from app.schemas.invoices import (
    InvoicePurchaseOrder,
    InvoicePurchaseOrderItem,
    SupplierInvoiceCreate,
    SupplierInvoiceDetail,
    SupplierInvoiceSummary,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _load(db: Session, invoice_id: uuid.UUID) -> SupplierInvoice | None:
    return db.scalar(
        select(SupplierInvoice)
        .options(
            selectinload(SupplierInvoice.vendor),
            selectinload(SupplierInvoice.purchase_order),
            selectinload(SupplierInvoice.items),
        )
        .where(SupplierInvoice.id == invoice_id)
    )


def _summary(invoice: SupplierInvoice) -> SupplierInvoiceSummary:
    return SupplierInvoiceSummary(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        vendor_id=invoice.vendor_id,
        supplier_name=invoice.vendor.legal_name,
        supplier_code=invoice.vendor.vendor_code,
        purchase_order_id=invoice.purchase_order_id,
        po_number=invoice.purchase_order.po_number,
        invoice_date=invoice.invoice_date,
        due_date=invoice.due_date,
        currency=invoice.currency,
        subtotal=invoice.subtotal,
        tax_amount=invoice.tax_amount,
        total_amount=invoice.total_amount,
        status=invoice.status,
        created_by_user_id=invoice.created_by_user_id,
        validated_at=invoice.validated_at,
        payment_reference=invoice.payment_reference,
        paid_at=invoice.paid_at,
        paid_by_user_id=invoice.paid_by_user_id,
        created_at=invoice.created_at,
    )


def _detail(invoice: SupplierInvoice) -> SupplierInvoiceDetail:
    return SupplierInvoiceDetail(
        **_summary(invoice).model_dump(),
        notes=invoice.notes,
        items=[
            {
                "id": item.id,
                "purchase_order_item_id": item.purchase_order_item_id,
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "line_total": item.line_total,
            }
            for item in invoice.items
        ],
    )


def _view_permissions():
    return require_any_permissions("invoices.review", "finance.review", "sourcing.manage")


@router.get("/purchase-orders", response_model=list[InvoicePurchaseOrder])
def invoice_purchase_orders(
    actor: User = Depends(_view_permissions()),
    db: Session = Depends(get_db),
):
    orders = db.scalars(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.vendor), selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.status == "ISSUED")
        .order_by(PurchaseOrder.po_date.desc(), PurchaseOrder.created_at.desc())
    ).all()
    return [
        InvoicePurchaseOrder(
            purchase_order_id=po.id,
            po_number=po.po_number,
            vendor_id=po.vendor_id,
            supplier_name=po.vendor.legal_name,
            supplier_code=po.vendor.vendor_code,
            currency=po.currency,
            total_amount=po.total_amount,
            payment_terms_days=po.payment_terms_days,
            status=po.status,
            items=[
                InvoicePurchaseOrderItem(
                    purchase_order_item_id=item.id,
                    name=item.name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    line_total=item.line_total,
                )
                for item in po.items
            ],
        )
        for po in orders
    ]


@router.get("", response_model=list[SupplierInvoiceSummary])
def list_invoices(
    actor: User = Depends(_view_permissions()),
    db: Session = Depends(get_db),
):
    invoices = db.scalars(
        select(SupplierInvoice)
        .options(selectinload(SupplierInvoice.vendor), selectinload(SupplierInvoice.purchase_order))
        .order_by(SupplierInvoice.created_at.desc())
    ).all()
    return [_summary(invoice) for invoice in invoices]


@router.get("/{invoice_id}", response_model=SupplierInvoiceDetail)
def get_invoice(
    invoice_id: uuid.UUID,
    actor: User = Depends(_view_permissions()),
    db: Session = Depends(get_db),
):
    invoice = _load(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _detail(invoice)


@router.post("", response_model=SupplierInvoiceDetail, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: SupplierInvoiceCreate,
    actor: User = Depends(require_permissions("invoices.review")),
    db: Session = Depends(get_db),
):
    po = db.scalar(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.vendor), selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.id == payload.purchase_order_id)
    )
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status != "ISSUED":
        raise HTTPException(status_code=409, detail="Invoices can only be captured against an issued purchase order.")
    if po.vendor_id != payload.vendor_id:
        raise HTTPException(status_code=422, detail="Invoice supplier must match the purchase order supplier.")
    if payload.currency.upper() != po.currency.upper():
        raise HTTPException(status_code=422, detail="Invoice currency must match the purchase order currency.")

    existing = db.scalar(
        select(SupplierInvoice.id).where(
            SupplierInvoice.vendor_id == payload.vendor_id,
            SupplierInvoice.invoice_number == payload.invoice_number.strip(),
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="An invoice with this supplier invoice number already exists.")

    po_items = {item.id: item for item in po.items}
    requested_ids = [item.purchase_order_item_id for item in payload.items]
    if len(requested_ids) != len(set(requested_ids)):
        raise HTTPException(status_code=422, detail="Each purchase-order line can appear only once on an invoice.")
    if any(item_id not in po_items for item_id in requested_ids):
        raise HTTPException(status_code=422, detail="One or more invoice lines do not belong to the selected purchase order.")

    invoice = SupplierInvoice(
        invoice_number=payload.invoice_number.strip(),
        vendor_id=payload.vendor_id,
        purchase_order_id=payload.purchase_order_id,
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
        currency=payload.currency.upper(),
        subtotal=payload.subtotal,
        tax_amount=payload.tax_amount,
        total_amount=payload.total_amount,
        status="RECEIVED",
        notes=payload.notes.strip() if payload.notes else None,
        created_by_user_id=actor.id,
    )
    for line in payload.items:
        invoice.items.append(
            SupplierInvoiceItem(
                purchase_order_item_id=line.purchase_order_item_id,
                description=line.description.strip(),
                quantity=line.quantity,
                unit_price=line.unit_price,
                line_total=line.line_total,
            )
        )
    db.add(invoice)
    db.flush()
    record_audit_event(
        db,
        actor_type=ActorType.HUMAN,
        actor_user_id=actor.id,
        action="SUPPLIER_INVOICE_RECEIVED",
        entity_type="supplier_invoice",
        entity_id=str(invoice.id),
        details={"invoice_number": invoice.invoice_number, "po_number": po.po_number, "status": invoice.status},
    )
    db.commit()
    return _detail(_load(db, invoice.id))


@router.post("/{invoice_id}/validate", response_model=SupplierInvoiceDetail)
def validate_invoice(
    invoice_id: uuid.UUID,
    actor: User = Depends(require_permissions("invoices.review")),
    db: Session = Depends(get_db),
):
    invoice = _load(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status != "RECEIVED":
        raise HTTPException(status_code=409, detail=f"Only received invoices can enter validation (current status: {invoice.status}).")
    invoice.status = "VALIDATING"
    invoice.validated_at = datetime.now(timezone.utc)
    record_audit_event(
        db,
        actor_type=ActorType.HUMAN,
        actor_user_id=actor.id,
        action="SUPPLIER_INVOICE_VALIDATED",
        entity_type="supplier_invoice",
        entity_id=str(invoice.id),
        details={"invoice_number": invoice.invoice_number, "to_status": invoice.status},
    )
    db.commit()
    return _detail(_load(db, invoice.id))


@router.post("/{invoice_id}/send-to-matching", response_model=SupplierInvoiceDetail)
def send_invoice_to_matching(
    invoice_id: uuid.UUID,
    actor: User = Depends(require_permissions("invoices.review")),
    db: Session = Depends(get_db),
):
    invoice = _load(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status != "VALIDATING":
        raise HTTPException(status_code=409, detail=f"Only validating invoices can enter matching (current status: {invoice.status}).")
    invoice.status = "MATCHING"
    record_audit_event(
        db,
        actor_type=ActorType.HUMAN,
        actor_user_id=actor.id,
        action="SUPPLIER_INVOICE_SENT_TO_MATCHING",
        entity_type="supplier_invoice",
        entity_id=str(invoice.id),
        details={"invoice_number": invoice.invoice_number, "to_status": invoice.status},
    )
    db.commit()
    return _detail(_load(db, invoice.id))
