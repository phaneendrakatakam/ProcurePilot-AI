import secrets
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies.auth import require_any_permissions, require_permissions
from app.core.database import get_db
from app.models.governance import ActorType
from app.models.identity import User
from app.models.procurement import PurchaseOrder, PurchaseOrderItem
from app.models.goods_receipts import GoodsReceipt, GoodsReceiptItem
from app.schemas.goods_receipts import (
    GoodsReceiptCreate,
    GoodsReceiptDetail,
    GoodsReceiptItemResponse,
    GoodsReceiptOpenItem,
    GoodsReceiptOpenPurchaseOrder,
    GoodsReceiptSummary,
)
from app.services.audit import record_audit_event
from app.services.purchase_requests import append_request_event

router = APIRouter(prefix="/goods-receipts", tags=["goods-receipts"])


def _load(db: Session, receipt_id: uuid.UUID) -> GoodsReceipt | None:
    return db.scalar(
        select(GoodsReceipt)
        .options(
            selectinload(GoodsReceipt.purchase_order),
            selectinload(GoodsReceipt.received_by),
            selectinload(GoodsReceipt.items).selectinload(GoodsReceiptItem.purchase_order_item),
        )
        .where(GoodsReceipt.id == receipt_id)
    )


def _summary(receipt: GoodsReceipt) -> GoodsReceiptSummary:
    return GoodsReceiptSummary(
        id=receipt.id,
        receipt_number=receipt.receipt_number,
        purchase_order_id=receipt.purchase_order_id,
        po_number=receipt.purchase_order.po_number,
        status=receipt.status,
        receipt_date=receipt.receipt_date,
        delivery_reference=receipt.delivery_reference,
        received_by_user_id=receipt.received_by_user_id,
        received_by_name=receipt.received_by.full_name if receipt.received_by else None,
        posted_at=receipt.posted_at,
        created_at=receipt.created_at,
    )


def _detail(receipt: GoodsReceipt) -> GoodsReceiptDetail:
    return GoodsReceiptDetail(
        **_summary(receipt).model_dump(),
        notes=receipt.notes,
        items=[
            GoodsReceiptItemResponse.model_validate(item, from_attributes=True).model_copy(update={"item_name": item.purchase_order_item.name if item.purchase_order_item else None})
            for item in receipt.items
        ],
    )


def _posted_quantity(
    db: Session,
    purchase_order_item_id: uuid.UUID,
) -> Decimal:
    value = db.scalar(
        select(func.coalesce(func.sum(GoodsReceiptItem.received_quantity), 0))
        .join(GoodsReceipt, GoodsReceipt.id == GoodsReceiptItem.goods_receipt_id)
        .where(
            GoodsReceiptItem.purchase_order_item_id == purchase_order_item_id,
            GoodsReceipt.status == "POSTED",
        )
    )
    return Decimal(value or 0)


def _receiving_status(db: Session, po: PurchaseOrder) -> str:
    """Derive the operational receiving status from posted receipt quantities."""
    if not po.items:
        return "EXPECTED"
    received_any = False
    remaining_any = False
    for po_item in po.items:
        received = _posted_quantity(db, po_item.id)
        if received > 0:
            received_any = True
        if Decimal(po_item.quantity) - received > 0:
            remaining_any = True
    if not received_any:
        return "EXPECTED"
    return "PARTIALLY_RECEIVED" if remaining_any else "FULLY_RECEIVED"




@router.get("/expected-deliveries", response_model=list[GoodsReceiptOpenPurchaseOrder])
@router.get("/eligible-orders", response_model=list[GoodsReceiptOpenPurchaseOrder])
def list_receivable_purchase_orders(
    actor: User = Depends(require_any_permissions("goods_receipts.manage", "sourcing.manage")),
    db: Session = Depends(get_db),
):
    """Return issued purchase orders that still have quantities available to receive."""
    rows = db.scalars(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.request),
            selectinload(PurchaseOrder.vendor),
            selectinload(PurchaseOrder.items),
        )
        .where(PurchaseOrder.status == "ISSUED")
        .order_by(PurchaseOrder.required_date.asc().nulls_last(), PurchaseOrder.created_at.desc())
    ).all()

    result = []
    for po in rows:
        items = []
        for po_item in po.items:
            received = _posted_quantity(db, po_item.id)
            remaining = Decimal(po_item.quantity) - received
            if remaining <= 0:
                continue
            items.append(GoodsReceiptOpenItem(
                purchase_order_item_id=po_item.id,
                name=po_item.name,
                ordered_quantity=po_item.quantity,
                received_quantity=received,
                remaining_quantity=remaining,
                unit_price=po_item.unit_price,
                currency=po.currency,
            ))
        if items:
            result.append(GoodsReceiptOpenPurchaseOrder(
                purchase_order_id=po.id,
                po_number=po.po_number,
                request_number=po.request.request_number,
                supplier_name=po.vendor.legal_name,
                supplier_code=po.vendor.vendor_code,
                currency=po.currency,
                required_date=po.required_date,
                delivery_days=int(po.delivery_days),
                status=po.status,
                receiving_status=_receiving_status(db, po),
                items=items,
            ))
    return result

@router.get("", response_model=list[GoodsReceiptSummary])
def list_goods_receipts(
    actor: User = Depends(require_any_permissions("goods_receipts.manage", "sourcing.manage")),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(GoodsReceipt)
        .options(selectinload(GoodsReceipt.purchase_order))
        .order_by(GoodsReceipt.created_at.desc())
    ).all()
    return [_summary(row) for row in rows]


@router.get("/purchase-orders/{purchase_order_id}/history", response_model=list[GoodsReceiptSummary])
def list_purchase_order_receipt_history(
    purchase_order_id: uuid.UUID,
    actor: User = Depends(require_any_permissions("goods_receipts.manage", "sourcing.manage")),
    db: Session = Depends(get_db),
):
    """Return the chronological receipt history for a purchase order."""
    po = db.scalar(select(PurchaseOrder.id).where(PurchaseOrder.id == purchase_order_id))
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    rows = db.scalars(
        select(GoodsReceipt)
        .options(selectinload(GoodsReceipt.purchase_order))
        .where(GoodsReceipt.purchase_order_id == purchase_order_id)
        .order_by(GoodsReceipt.receipt_date.desc(), GoodsReceipt.created_at.desc())
    ).all()
    return [_summary(row) for row in rows]


@router.get("/{receipt_id}", response_model=GoodsReceiptDetail)
def get_goods_receipt(
    receipt_id: uuid.UUID,
    actor: User = Depends(require_any_permissions("goods_receipts.manage", "sourcing.manage")),
    db: Session = Depends(get_db),
):
    receipt = _load(db, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Goods receipt not found")
    return _detail(receipt)


@router.post("", response_model=GoodsReceiptDetail, status_code=status.HTTP_201_CREATED)
def create_goods_receipt(
    payload: GoodsReceiptCreate,
    actor: User = Depends(require_permissions("goods_receipts.manage")),
    db: Session = Depends(get_db),
):
    po = db.scalar(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.id == payload.purchase_order_id)
    )
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status != "ISSUED":
        raise HTTPException(
            status_code=409,
            detail=f"Goods can only be received against an issued purchase order (current status: {po.status})",
        )

    requested_ids = [item.purchase_order_item_id for item in payload.items]
    if len(requested_ids) != len(set(requested_ids)):
        raise HTTPException(status_code=422, detail="Each purchase-order line can appear only once in a goods receipt.")

    po_items = {item.id: item for item in po.items}
    missing = [str(item_id) for item_id in requested_ids if item_id not in po_items]
    if missing:
        raise HTTPException(status_code=422, detail="One or more receipt lines do not belong to the selected purchase order.")

    receipt = GoodsReceipt(
        receipt_number=f"GR-{datetime.now(timezone.utc).year}-{secrets.token_hex(3).upper()}",
        purchase_order_id=po.id,
        received_by_user_id=actor.id,
        receipt_date=payload.receipt_date,
        status="DRAFT",
        delivery_reference=payload.delivery_reference.strip() if payload.delivery_reference else None,
        notes=payload.notes.strip() if payload.notes else None,
    )

    for line in payload.items:
        po_item = po_items[line.purchase_order_item_id]
        already_received = _posted_quantity(db, po_item.id)
        remaining = Decimal(po_item.quantity) - already_received
        if line.received_quantity > remaining:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Receipt quantity for '{po_item.name}' exceeds the remaining quantity "
                    f"({remaining})."
                ),
            )
        receipt.items.append(
            GoodsReceiptItem(
                purchase_order_item_id=po_item.id,
                received_quantity=line.received_quantity,
                accepted_quantity=line.accepted_quantity,
                rejected_quantity=line.rejected_quantity,
                rejection_reason=(line.rejection_reason.strip() if line.rejection_reason else None),
            )
        )

    db.add(receipt)
    db.flush()

    record_audit_event(
        db,
        actor_type=ActorType.HUMAN,
        actor_user_id=actor.id,
        action="GOODS_RECEIPT_CREATED",
        entity_type="goods_receipt",
        entity_id=str(receipt.id),
        details={
            "receipt_number": receipt.receipt_number,
            "po_number": po.po_number,
            "status": receipt.status,
        },
    )
    db.commit()
    return _detail(_load(db, receipt.id))


@router.post("/{receipt_id}/post", response_model=GoodsReceiptDetail)
def post_goods_receipt(
    receipt_id: uuid.UUID,
    actor: User = Depends(require_permissions("goods_receipts.manage")),
    db: Session = Depends(get_db),
):
    receipt = _load(db, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Goods receipt not found")
    if receipt.status != "DRAFT":
        raise HTTPException(
            status_code=409,
            detail=f"Only draft goods receipts can be posted (current status: {receipt.status})",
        )

    po = db.scalar(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.id == receipt.purchase_order_id)
    )
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status != "ISSUED":
        raise HTTPException(status_code=409, detail="The purchase order must remain issued before the receipt can be posted.")

    po_items = {item.id: item for item in po.items}
    for line in receipt.items:
        po_item = po_items.get(line.purchase_order_item_id)
        if not po_item:
            raise HTTPException(status_code=409, detail="Receipt contains a line that no longer belongs to the purchase order.")
        already_received = _posted_quantity(db, po_item.id)
        remaining = Decimal(po_item.quantity) - already_received
        if Decimal(line.received_quantity) > remaining:
            raise HTTPException(
                status_code=409,
                detail=f"Receipt quantity for '{po_item.name}' exceeds the remaining quantity ({remaining}).",
            )

    previous_receiving_status = _receiving_status(db, po)
    receipt.status = "POSTED"
    receipt.posted_at = datetime.now(timezone.utc)
    receiving_status = _receiving_status(db, po)

    append_request_event(
        po.request,
        actor_type="HUMAN",
        actor_user_id=actor.id,
        event_type="GOODS_RECEIPT_POSTED",
        from_status=po.request.status,
        to_status=po.request.status,
        details={
            "receipt_number": receipt.receipt_number,
            "po_number": po.po_number,
            "goods_receipt_id": str(receipt.id),
        },
    )
    record_audit_event(
        db,
        actor_type=ActorType.HUMAN,
        actor_user_id=actor.id,
        action="GOODS_RECEIPT_POSTED",
        entity_type="goods_receipt",
        entity_id=str(receipt.id),
        details={
            "receipt_number": receipt.receipt_number,
            "po_number": po.po_number,
            "posted_at": receipt.posted_at.isoformat(),
            "receiving_status": receiving_status,
            "previous_receiving_status": previous_receiving_status,
        },
    )
    if previous_receiving_status != receiving_status:
        record_audit_event(
            db,
            actor_type=ActorType.HUMAN,
            actor_user_id=actor.id,
            action="PURCHASE_ORDER_RECEIVING_STATUS_CHANGED",
        entity_type="purchase_order",
        entity_id=str(po.id),
            details={
                "po_number": po.po_number,
                "from_status": previous_receiving_status,
                "to_status": receiving_status,
                "receipt_number": receipt.receipt_number,
            },
        )
    db.commit()
    return _detail(_load(db, receipt.id))
