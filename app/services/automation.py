from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.governance import ActorType
from app.models.goods_receipts import GoodsReceipt, GoodsReceiptItem
from app.models.identity import Role, User, UserRole
from app.models.invoice_matching import SupplierInvoiceMatch
from app.models.invoices import SupplierInvoice
from app.models.notifications import Notification
from app.models.procurement import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseRequestApproval,
    RFQ,
    RFQSupplier,
)
from app.services.audit import record_audit_event
from app.services.supplier_email import build_automation_email, send_email


AUTOMATION_TYPES = {
    "RFQ_RESPONSE_REMINDER",
    "DELIVERY_APPROACHING",
    "INVOICE_EXCEPTION",
    "APPROVAL_PENDING_REMINDER",
}


def _now_utc(now: datetime | None = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _create_notification(
    db: Session,
    *,
    notification_type: str,
    recipient_user_id: Any,
    recipient_email: str,
    subject: str,
    body: str,
    entity_type: str,
    entity_id: str,
    dedupe_key: str,
    dry_run: bool,
    planned: list[dict[str, Any]],
) -> str:
    existing = db.scalar(select(Notification).where(Notification.dedupe_key == dedupe_key))
    if existing and existing.status == "SENT":
        return "skipped"
    if existing and existing.status == "PENDING":
        return "skipped"

    planned_item = {
        "notification_type": notification_type,
        "recipient_email": recipient_email,
        "subject": subject,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "dedupe_key": dedupe_key,
    }
    planned.append(planned_item)
    if dry_run:
        return "planned"

    notification = existing or Notification(
        recipient_user_id=recipient_user_id,
        recipient_email=recipient_email,
        notification_type=notification_type,
        channel="EMAIL",
        subject=subject,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        dedupe_key=dedupe_key,
    )
    notification.recipient_user_id = recipient_user_id
    notification.recipient_email = recipient_email
    notification.subject = subject
    notification.body = body
    notification.status = "PENDING"
    notification.error = None
    db.add(notification)
    db.flush()

    try:
        send_email(build_automation_email(to_email=recipient_email, subject=subject, body=body))
        notification.status = "SENT"
        notification.sent_at = _now_utc()
        record_audit_event(
            db,
            actor_type=ActorType.SYSTEM,
            action="AUTOMATION_NOTIFICATION_SENT",
            entity_type=entity_type,
            entity_id=entity_id,
            details={"notification_type": notification_type, "recipient_email": recipient_email},
        )
    except Exception as exc:
        notification.status = "FAILED"
        notification.error = str(exc)[:500]
        record_audit_event(
            db,
            actor_type=ActorType.SYSTEM,
            action="AUTOMATION_NOTIFICATION_FAILED",
            entity_type=entity_type,
            entity_id=entity_id,
            details={"notification_type": notification_type, "recipient_email": recipient_email, "error": str(exc)[:500]},
        )
    return "sent" if notification.status == "SENT" else "failed"


def _internal_recipients(db: Session, role_codes: set[str]) -> list[User]:
    rows = db.scalars(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(User.is_active.is_(True), Role.code.in_(role_codes))
        .order_by(User.email)
    ).all()
    seen: set[str] = set()
    result: list[User] = []
    for user in rows:
        if user.email.lower() not in seen:
            seen.add(user.email.lower())
            result.append(user)
    return result


def _outstanding_quantities(db: Session, po: PurchaseOrder) -> dict[Any, float]:
    totals = {item.id: float(item.quantity) for item in po.items}
    received: dict[Any, float] = {item_id: 0.0 for item_id in totals}
    receipts = db.scalars(
        select(GoodsReceipt)
        .options(selectinload(GoodsReceipt.items))
        .where(GoodsReceipt.purchase_order_id == po.id, GoodsReceipt.status == "POSTED")
    ).all()
    for receipt in receipts:
        for item in receipt.items:
            if item.purchase_order_item_id in received:
                received[item.purchase_order_item_id] += float(item.accepted_quantity)
    return {item_id: max(qty - received.get(item_id, 0.0), 0.0) for item_id, qty in totals.items()}


def run_automations(db: Session, *, now: datetime | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Run all notification automation rules once. Safe to call repeatedly."""
    now = _now_utc(now)
    planned: list[dict[str, Any]] = []
    failures = 0

    if not settings.automation_enabled:
        return {"enabled": False, "dry_run": dry_run, "planned": [], "sent": 0, "failed": 0}

    # 1. RFQ supplier response reminders.
    rfq_cutoff = now + timedelta(hours=settings.automation_rfq_reminder_hours)
    rfqs = db.scalars(
        select(RFQ)
        .options(selectinload(RFQ.request), selectinload(RFQ.suppliers).selectinload(RFQSupplier.vendor))
        .where(RFQ.status == "SENT", RFQ.response_deadline <= rfq_cutoff, RFQ.response_deadline > now)
    ).all()
    for rfq in rfqs:
        for supplier in rfq.suppliers:
            if supplier.status != "SENT" or supplier.response_submitted_at is not None:
                continue
            deadline_day = rfq.response_deadline.date().isoformat()
            subject = f"Reminder: RFQ {rfq.rfq_number} response due soon"
            body = (
                f"Hello {supplier.vendor.contact_person or supplier.vendor.legal_name},\n\n"
                f"This is a reminder that quotation response for RFQ {rfq.rfq_number} "
                f"({rfq.request.title}) is due by {rfq.response_deadline.strftime('%d %b %Y, %H:%M UTC')}.\n\n"
                "Please use the secure invitation link from the original RFQ email to submit your quotation.\n\n"
                "ProcurePilot"
            )
            _create_notification(
                db, notification_type="RFQ_RESPONSE_REMINDER", recipient_user_id=None,
                recipient_email=supplier.vendor.email, subject=subject, body=body,
                entity_type="rfq_supplier", entity_id=str(supplier.id),
                dedupe_key=f"rfq-response-reminder:{supplier.id}:{deadline_day}",
                dry_run=dry_run, planned=planned,
            )

    # 2. Approvals waiting beyond the reminder threshold.
    approval_cutoff = now - timedelta(hours=settings.automation_approval_reminder_hours)
    approvals = db.scalars(
        select(PurchaseRequestApproval)
        .options(selectinload(PurchaseRequestApproval.request), selectinload(PurchaseRequestApproval.approver))
        .where(PurchaseRequestApproval.status == "PENDING", PurchaseRequestApproval.created_at <= approval_cutoff)
    ).all()
    for approval in approvals:
        request = approval.request
        if not request or request.status != "PENDING_APPROVAL" or not approval.approver or not approval.approver.is_active:
            continue
        day = now.date().isoformat()
        subject = f"Approval reminder: {request.request_number} needs your decision"
        body = (
            f"Hello {approval.approver.full_name},\n\n"
            f"Purchase request {request.request_number} ({request.title}) is still waiting for your "
            f"approval decision.\n\nPlease review the assigned approval in ProcurePilot.\n\nProcurePilot"
        )
        _create_notification(
            db, notification_type="APPROVAL_PENDING_REMINDER", recipient_user_id=approval.approver.id,
            recipient_email=approval.approver.email, subject=subject, body=body,
            entity_type="purchase_request_approval", entity_id=str(approval.id),
            dedupe_key=f"approval-reminder:{approval.id}:{day}", dry_run=dry_run, planned=planned,
        )

    # 3. Expected delivery approaching, only where quantity remains.
    delivery_cutoff = now.date() + timedelta(days=settings.automation_delivery_reminder_days)
    purchase_orders = db.scalars(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.status == "ISSUED")
    ).all()
    receivers = _internal_recipients(db, {"GOODS_RECEIVER"})
    for po in purchase_orders:
        outstanding = _outstanding_quantities(db, po)
        if not any(value > 0 for value in outstanding.values()):
            continue
        if po.required_date:
            expected_date = po.required_date
        elif po.issued_at:
            expected_date = (po.issued_at + timedelta(days=int(po.delivery_days))).date()
        else:
            continue
        if expected_date < now.date() or expected_date > delivery_cutoff:
            continue
        for receiver in receivers:
            subject = f"Delivery reminder: {po.po_number} is approaching"
            body = (
                f"Hello {receiver.full_name},\n\n"
                f"Purchase order {po.po_number} has outstanding quantity and an expected delivery date of "
                f"{expected_date.strftime('%d %b %Y')}.\n\nPlease review Expected Deliveries and prepare receiving.\n\nProcurePilot"
            )
            _create_notification(
                db, notification_type="DELIVERY_APPROACHING", recipient_user_id=receiver.id,
                recipient_email=receiver.email, subject=subject, body=body,
                entity_type="purchase_order", entity_id=str(po.id),
                dedupe_key=f"delivery-approaching:{po.id}:{expected_date.isoformat()}:{receiver.id}",
                dry_run=dry_run, planned=planned,
            )

    # 4. Invoice or persisted 3-way-match exceptions go to Finance/AP.
    finance_recipients = _internal_recipients(db, {"AP_ANALYST", "FINANCE_MANAGER"})
    invoices = db.scalars(
        select(SupplierInvoice)
        .options(selectinload(SupplierInvoice.vendor), selectinload(SupplierInvoice.purchase_order))
        .where(SupplierInvoice.status == "EXCEPTION")
    ).all()
    matches = db.scalars(
        select(SupplierInvoiceMatch)
        .options(selectinload(SupplierInvoiceMatch.invoice), selectinload(SupplierInvoiceMatch.purchase_order))
        .where(SupplierInvoiceMatch.result == "EXCEPTION")
    ).all()
    exception_entities: dict[str, tuple[str, str, str]] = {}
    for invoice in invoices:
        exception_entities[f"invoice:{invoice.id}"] = ("supplier_invoice", str(invoice.id), f"Invoice {invoice.invoice_number} requires Finance attention.")
    for match in matches:
        exception_entities[f"match:{match.id}"] = (
            "supplier_invoice_match", str(match.id),
            f"3-way match exception for invoice {match.invoice.invoice_number if match.invoice else 'unknown invoice'} requires Finance attention.",
        )
    for _, (entity_type, entity_id, summary) in exception_entities.items():
        for recipient in finance_recipients:
            subject = "Finance action required: procurement exception"
            body = f"Hello {recipient.full_name},\n\n{summary}\n\nPlease review the invoice or 3-way match exception in ProcurePilot.\n\nProcurePilot"
            _create_notification(
                db, notification_type="INVOICE_EXCEPTION", recipient_user_id=recipient.id,
                recipient_email=recipient.email, subject=subject, body=body,
                entity_type=entity_type, entity_id=entity_id,
                dedupe_key=f"invoice-exception:{entity_type}:{entity_id}:{recipient.id}",
                dry_run=dry_run, planned=planned,
            )

    if not dry_run:
        db.commit()
        keys = {item["dedupe_key"] for item in planned if "dedupe_key" in item}
        rows = db.scalars(select(Notification).where(Notification.dedupe_key.in_(keys))).all() if keys else []
        sent = sum(1 for row in rows if row.status == "SENT")
        failures = sum(1 for row in rows if row.status == "FAILED")
    else:
        sent = 0
        failures = 0
    return {"enabled": True, "dry_run": dry_run, "planned": planned, "sent": sent, "failed": failures}
