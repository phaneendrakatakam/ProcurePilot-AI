from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.models.goods_receipts import GoodsReceipt, GoodsReceiptItem
from app.models.identity import User
from app.models.invoice_matching import SupplierInvoiceMatch
from app.models.invoices import SupplierInvoice
from app.models.procurement import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseRequest,
    PurchaseRequestApproval,
    RFQ,
    RFQSupplier,
)
from app.schemas.dashboard import DashboardResponse
from app.services.auth import get_role_codes

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

TERMINAL_REQUEST_STATES = {"REJECTED", "CANCELLED", "COMPLETED", "CLOSED"}


def _role(user: User) -> str:
    roles = get_role_codes(user)
    if "ADMINISTRATOR" in roles:
        return "ADMINISTRATOR"
    return roles[0] if roles else "EMPLOYEE"


def _scope_requests(stmt, user: User, role: str):
    if role == "EMPLOYEE":
        return stmt.where(PurchaseRequest.requester_id == user.id)
    if role == "MANAGER":
        return stmt.where(PurchaseRequest.department_id == user.department_id)
    return stmt


def _money(value: Decimal | None) -> float:
    return float(value or Decimal("0"))


def _request_items(rows):
    return [
        {
            "id": str(r.id),
            "number": r.request_number,
            "title": r.title,
            "status": r.status,
            "amount": _money(r.estimated_total),
            "required_date": r.required_date.isoformat() if r.required_date else None,
            "department": r.department.name if r.department else None,
        }
        for r in rows
    ]


@router.get("", response_model=DashboardResponse)
def get_dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    role = _role(user)

    request_stmt = select(PurchaseRequest).options(selectinload(PurchaseRequest.department)).order_by(PurchaseRequest.created_at.desc())
    request_stmt = _scope_requests(request_stmt, user, role)
    requests = db.scalars(request_stmt).all()

    approval_stmt = select(PurchaseRequestApproval).options(
        selectinload(PurchaseRequestApproval.request)
    ).where(PurchaseRequestApproval.status == "PENDING").order_by(PurchaseRequestApproval.created_at.asc())
    if role in {"MANAGER", "FINANCE_MANAGER"}:
        approval_stmt = approval_stmt.where(PurchaseRequestApproval.approver_user_id == user.id)
    elif role in {"AP_ANALYST", "EMPLOYEE", "GOODS_RECEIVER"}:
        approval_stmt = approval_stmt.where(PurchaseRequestApproval.id == None)
    approvals = db.scalars(approval_stmt).all()

    rfq_stmt = select(RFQ).options(selectinload(RFQ.request)).order_by(RFQ.created_at.desc())
    if role in {"EMPLOYEE", "MANAGER"}:
        rfq_stmt = rfq_stmt.join(PurchaseRequest, PurchaseRequest.id == RFQ.request_id)
        rfq_stmt = _scope_requests(rfq_stmt, user, role)
    rfqs = db.scalars(rfq_stmt).unique().all()

    supplier_stmt = select(RFQSupplier).options(
        selectinload(RFQSupplier.rfq), selectinload(RFQSupplier.vendor)
    ).where(RFQSupplier.status.in_(["INVITED", "SENT"]))
    pending_supplier_responses = db.scalars(supplier_stmt).all()

    po_stmt = select(PurchaseOrder).options(
        selectinload(PurchaseOrder.vendor), selectinload(PurchaseOrder.items)
    ).order_by(PurchaseOrder.created_at.desc())
    if role == "EMPLOYEE":
        po_stmt = po_stmt.join(PurchaseRequest, PurchaseRequest.id == PurchaseOrder.purchase_request_id).where(PurchaseRequest.requester_id == user.id)
    elif role == "MANAGER":
        po_stmt = po_stmt.join(PurchaseRequest, PurchaseRequest.id == PurchaseOrder.purchase_request_id).where(PurchaseRequest.department_id == user.department_id)
    purchase_orders = db.scalars(po_stmt).unique().all()

    issued_pos = [p for p in purchase_orders if p.status == "ISSUED"]
    po_item_ids = [item.id for po in issued_pos for item in po.items]
    received_by_item: dict = {}
    if po_item_ids:
        receipt_rows = db.execute(
            select(GoodsReceiptItem.purchase_order_item_id, func.coalesce(func.sum(GoodsReceiptItem.accepted_quantity), 0))
            .join(GoodsReceipt, GoodsReceipt.id == GoodsReceiptItem.goods_receipt_id)
            .where(GoodsReceiptItem.purchase_order_item_id.in_(po_item_ids), GoodsReceipt.status == "POSTED")
            .group_by(GoodsReceiptItem.purchase_order_item_id)
        ).all()
        received_by_item = {row[0]: Decimal(str(row[1])) for row in receipt_rows}

    expected_deliveries = []
    partial_po_ids = set()
    for po in issued_pos:
        remaining = Decimal("0")
        received = Decimal("0")
        ordered = Decimal("0")
        for item in po.items:
            ordered += item.quantity
            got = received_by_item.get(item.id, Decimal("0"))
            received += got
            remaining += max(item.quantity - got, Decimal("0"))
        if remaining > 0:
            if received > 0:
                partial_po_ids.add(po.id)
            expected_deliveries.append({
                "id": str(po.id), "number": po.po_number, "supplier": po.vendor.legal_name if po.vendor else None,
                "ordered_quantity": _money(ordered), "received_quantity": _money(received), "remaining_quantity": _money(remaining),
                "required_date": po.required_date.isoformat() if po.required_date else None,
            })

    invoice_stmt = select(SupplierInvoice).options(
        selectinload(SupplierInvoice.vendor), selectinload(SupplierInvoice.purchase_order)
    ).order_by(SupplierInvoice.created_at.desc())
    invoices = db.scalars(invoice_stmt).all()
    if role == "EMPLOYEE":
        request_ids = {r.id for r in requests}
        invoices = [i for i in invoices if i.purchase_order_id in {p.id for p in purchase_orders} or (i.purchase_order and i.purchase_order.purchase_request_id in request_ids)]
    elif role == "MANAGER":
        po_ids = {p.id for p in purchase_orders}
        invoices = [i for i in invoices if i.purchase_order_id in po_ids]

    match_stmt = select(SupplierInvoiceMatch).options(selectinload(SupplierInvoiceMatch.invoice)).where(SupplierInvoiceMatch.result == "EXCEPTION")
    matches = db.scalars(match_stmt).all()
    if role in {"EMPLOYEE", "MANAGER"}:
        po_ids = {p.id for p in purchase_orders}
        matches = [m for m in matches if m.purchase_order_id in po_ids]

    open_requests = [r for r in requests if r.status not in TERMINAL_REQUEST_STATES]
    pending_approvals = approvals
    awaiting_rfqs = {s.rfq_id for s in pending_supplier_responses if s.rfq and s.rfq.status == "SENT"}
    awaiting_issue = [p for p in purchase_orders if p.status in {"DRAFT", "PENDING_RELEASE"}]
    invoice_exceptions = [i for i in invoices if i.status == "EXCEPTION"]

    spend = sum((p.total_amount or Decimal("0")) for p in issued_pos)

    request_section = _request_items(open_requests[:8])
    approval_section = [
        {"id": str(a.id), "request_id": str(a.purchase_request_id), "request_number": a.request.request_number if a.request else None,
         "status": a.status, "sequence": a.sequence, "approver_role": a.approver_role}
        for a in pending_approvals[:8]
    ]
    rfq_section = [
        {"id": str(r.id), "number": r.rfq_number, "status": r.status, "request_number": r.request.request_number if r.request else None,
         "response_deadline": r.response_deadline.isoformat() if r.response_deadline else None}
        for r in rfqs[:8]
    ]
    po_section = [
        {"id": str(p.id), "number": p.po_number, "status": p.status, "supplier": p.vendor.legal_name if p.vendor else None,
         "total": _money(p.total_amount), "required_date": p.required_date.isoformat() if p.required_date else None}
        for p in purchase_orders[:8]
    ]
    invoice_section = [
        {"id": str(i.id), "number": i.invoice_number, "status": i.status, "supplier": i.vendor.legal_name if i.vendor else None,
         "total": _money(i.total_amount), "due_date": i.due_date.isoformat() if i.due_date else None}
        for i in invoices[:8]
    ]
    exception_section = [
        {"id": str(m.id), "invoice_id": str(m.invoice_id), "invoice_number": m.invoice.invoice_number if m.invoice else None,
         "result": m.result, "reason": m.exception_reason, "price_variance": _money(m.price_variance), "quantity_variance": _money(m.quantity_variance)}
        for m in matches[:8]
    ]

    if role == "EMPLOYEE":
        title = "My Procurement Command Center"
        sections = {"requests": request_section}
    elif role == "MANAGER":
        title = "Manager Command Center"
        sections = {"requests": request_section, "approvals": approval_section}
    elif role in {"PROCUREMENT_ANALYST", "PROCUREMENT_HEAD", "ADMINISTRATOR"}:
        title = "Procurement Command Center"
        sections = {"requests": request_section, "approvals": approval_section, "rfqs": rfq_section, "supplier_responses": [{"id": str(s.id), "rfq_id": str(s.rfq_id), "supplier": s.vendor.legal_name if s.vendor else None, "status": s.status} for s in pending_supplier_responses[:8]], "purchase_orders": po_section, "deliveries": expected_deliveries[:8], "invoices": invoice_section, "exceptions": exception_section}
    elif role == "FINANCE_MANAGER":
        title = "Finance Control Center"
        sections = {"approvals": approval_section, "invoices": invoice_section, "exceptions": exception_section}
    else:
        title = "Receiving Command Center"
        sections = {"deliveries": expected_deliveries[:8]}

    return DashboardResponse(
        role=role, title=title,
        kpis={
            "open_requests": len(open_requests),
            "pending_approvals": len(pending_approvals),
            "rfqs_awaiting_response": len(awaiting_rfqs),
            "pos_awaiting_issue": len(awaiting_issue),
            "expected_deliveries": len(expected_deliveries),
            "partial_receipts": len(partial_po_ids),
            "invoice_exceptions": len(invoice_exceptions),
            "three_way_match_exceptions": len(matches),
            "spend": _money(spend),
        },
        sections=sections,
    )
