import hashlib
from html import escape as html_escape
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.governance import ActorType
from app.models.procurement import PurchaseRequestItem, RFQ, RFQSupplier, SupplierQuotation, SupplierQuotationItem
from app.schemas.quotations import SupplierQuotationResponse, QuotationLineInput
from app.services.quotation_lines import normalized_lines
from app.services.audit import record_audit_event
from app.services.purchase_requests import append_request_event

router = APIRouter(prefix="/supplier-responses", tags=["supplier-responses"])


def _find_invitation(db: Session, token: str):
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return db.scalar(
        select(RFQSupplier)
        .options(
            selectinload(RFQSupplier.rfq).selectinload(RFQ.request),
            selectinload(RFQSupplier.vendor),
            selectinload(RFQSupplier.quotation),
        )
        .where(RFQSupplier.response_token_hash == token_hash)
    )


def _validate(invitation):
    if not invitation:
        raise HTTPException(status_code=404, detail="This quotation invitation is invalid or no longer available.")
    now = datetime.now(timezone.utc)
    if invitation.quotation is not None or invitation.response_submitted_at is not None:
        raise HTTPException(status_code=409, detail="A quotation has already been submitted for this invitation.")
    if invitation.status != "SENT":
        raise HTTPException(status_code=409, detail="This quotation invitation is no longer accepting responses.")
    if invitation.response_token_expires_at and invitation.response_token_expires_at < now:
        raise HTTPException(status_code=410, detail="This quotation invitation has expired.")
    if invitation.rfq.status != "SENT":
        raise HTTPException(status_code=409, detail="This RFQ is no longer accepting supplier responses.")
    return invitation


def _page(title: str, body: str, status_code: int = 200) -> HTMLResponse:
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>{title} · ProcurePilot</title><style>
    body{{margin:0;background:#f4f7f8;font-family:Inter,Arial,sans-serif;color:#102a43}}.wrap{{max-width:760px;margin:40px auto;padding:20px}}.card{{background:white;border:1px solid #dbe5e8;border-radius:18px;padding:28px;box-shadow:0 12px 35px rgba(16,42,67,.08)}}h1{{margin:6px 0 10px;font-size:30px}}h2{{font-size:18px}}.eyebrow{{color:#0f766e;font-weight:700;font-size:12px;letter-spacing:.12em}}.muted{{color:#64748b}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}label{{display:block;font-weight:600;font-size:14px}}input,textarea{{width:100%;box-sizing:border-box;margin-top:7px;padding:11px 12px;border:1px solid #cbd5df;border-radius:9px;font:inherit}}textarea{{min-height:110px;resize:vertical}}.full{{grid-column:1/-1}}button{{margin-top:20px;padding:12px 18px;border:0;border-radius:9px;background:#0f766e;color:white;font-weight:700;cursor:pointer}}.notice{{padding:13px 15px;border-radius:10px;background:#eef7f5;margin:18px 0}}.quoted-item{{padding:14px;margin:8px 0;border:1px solid #dbe5e8;border-radius:10px}}.quoted-item small{{display:block;color:#64748b;margin:5px 0}}@media(max-width:620px){{.wrap{{margin:10px auto;padding:10px}}.card{{padding:20px}}.grid{{grid-template-columns:1fr}}.full{{grid-column:auto}}}}
    </style></head><body><main class="wrap"><section class="card">{body}</section></main></body></html>'''
    return HTMLResponse(html, status_code=status_code, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


@router.get("/{token}", response_class=HTMLResponse, include_in_schema=False)
def quotation_form(token: str, db: Session = Depends(get_db)):
    try:
        invitation = _validate(_find_invitation(db, token))
    except HTTPException as exc:
        return _page("Quotation invitation", f'<span class="eyebrow">SUPPLIER RESPONSE</span><h1>Response unavailable</h1><p class="muted">{exc.detail}</p>', exc.status_code)

    request = invitation.rfq.request
    items = db.scalars(select(PurchaseRequestItem).where(PurchaseRequestItem.request_id == request.id)).all()
    item_html = "".join(
        f'<div class="quoted-item"><strong>{html_escape(item.name)}</strong>'
        f'<small>Requested quantity: {item.quantity} · {html_escape(item.description or "")}</small>'
        f'<div class="grid"><label>Quoted quantity<input name="quantity_{item.id}" type="number" min="0.01" step="0.01" value="{item.quantity}" required></label>'
        f'<label>Unit price ({html_escape(request.currency or "INR")})<input name="price_{item.id}" type="number" min="0.01" step="0.01" required></label></div></div>'
        for item in items
    )
    deadline = invitation.rfq.response_deadline.astimezone(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    body = f'''<span class="eyebrow">PROCUREPILOT · SUPPLIER RESPONSE</span>
    <h1>Submit your quotation</h1>
    <p class="muted">RFQ <strong>{html_escape(invitation.rfq.rfq_number)}</strong> · {html_escape(request.title)}</p>
    <div class="notice"><strong>{html_escape(invitation.vendor.legal_name)}</strong><br>Response deadline: {deadline}</div>
    <h2>Itemized quotation</h2><p class="muted">Price each requested item separately. All quantities must match the RFQ.</p>
    <form method="post">{item_html or '<p>No requested items are available.</p>'}<div class="grid">
      <label>Tax amount for all items<input name="tax_amount" type="number" min="0" step="0.01" value="0" required></label>
      <label>Delivery time (days)<input name="delivery_days" type="number" min="0" max="3650" step="1" value="0" required></label>
      <label>Quotation valid until<input name="valid_until" type="date" required></label>
      <label class="full">Supplier notes<textarea name="notes" maxlength="2000" placeholder="Commercial terms, exclusions, certifications, freight, payment terms, etc."></textarea></label>
    </div><button type="submit">Submit quotation</button></form>'''
    return _page("Submit quotation", body)


@router.post("/{token}", response_class=HTMLResponse, include_in_schema=False)
async def submit_quotation(
    token: str,
    request: Request,
    tax_amount: Decimal = Form(Decimal("0")),
    delivery_days: int = Form(0),
    valid_until: date = Form(...),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
):
    try:
        invitation = _validate(_find_invitation(db, token))
    except HTTPException as exc:
        return _page("Quotation response", f'<span class="eyebrow">SUPPLIER RESPONSE</span><h1>Response unavailable</h1><p class="muted">{exc.detail}</p>', exc.status_code)

    rfq_request = invitation.rfq.request
    request_items = db.scalars(select(PurchaseRequestItem).where(PurchaseRequestItem.request_id == rfq_request.id)).all()
    form = await request.form()
    try:
        submitted = [QuotationLineInput(
            request_item_id=item.id,
            quantity=Decimal(str(form[f"quantity_{item.id}"])),
            unit_price=Decimal(str(form[f"price_{item.id}"])),
        ) for item in request_items]
        lines = normalized_lines(request_items, submitted)
    except (KeyError, ValueError, ArithmeticError) as exc:
        return _page("Quotation response", f'<h1>Check itemized prices</h1><p>{html_escape(str(exc))}</p>', 422)
    subtotal = sum((amount for _, _, _, amount in lines), Decimal("0.00"))
    payload = SupplierQuotationResponse(
        quoted_quantity=Decimal("1.00"), unit_price=subtotal,
        tax_amount=tax_amount, delivery_days=delivery_days, valid_until=valid_until, notes=notes,
    )
    if payload.valid_until < date.today():
        return _page("Quotation response", '<span class="eyebrow">SUPPLIER RESPONSE</span><h1>Check the quotation validity date</h1><p class="muted">The quotation validity date cannot be in the past.</p>', 422)

    request = invitation.rfq.request
    currency = request.currency or "INR"
    total = (subtotal + payload.tax_amount).quantize(Decimal("0.01"))
    now = datetime.now(timezone.utc)
    quotation = SupplierQuotation(
        rfq_id=invitation.rfq.id,
        rfq_supplier_id=invitation.id,
        currency=currency,
        quoted_quantity=payload.quoted_quantity,
        unit_price=payload.unit_price,
        subtotal=subtotal,
        tax_amount=payload.tax_amount,
        total_amount=total,
        delivery_days=payload.delivery_days,
        valid_until=payload.valid_until,
        notes=payload.notes.strip() if payload.notes else None,
        status="RECEIVED",
        received_at=now,
        recorded_by_user_id=None,
        submission_source="SUPPLIER_PORTAL",
    )
    db.add(quotation)
    db.flush()
    for item, qty, price, amount in lines:
        quotation.items.append(SupplierQuotationItem(
            request_item_id=item.id, quantity=qty, unit_price=price, line_total=amount,
        ))
    invitation.response_submitted_at = now
    invitation.status = "RESPONDED"
    append_request_event(
        request,
        actor_type="SYSTEM",
        event_type="QUOTATION_RECEIVED",
        details={
            "rfq_number": invitation.rfq.rfq_number,
            "supplier_code": invitation.vendor.vendor_code,
            "supplier_name": invitation.vendor.legal_name,
            "quotation_id": str(quotation.id),
            "total_amount": str(total),
            "source": "SUPPLIER_PORTAL",
        },
    )
    record_audit_event(
        db,
        actor_type=ActorType.SYSTEM,
        action="QUOTATION_RECEIVED",
        entity_type="supplier_quotation",
        entity_id=str(quotation.id),
        details={
            "rfq_number": invitation.rfq.rfq_number,
            "supplier_code": invitation.vendor.vendor_code,
            "total_amount": str(total),
            "source": "SUPPLIER_PORTAL",
        },
    )
    db.commit()
    return _page("Quotation submitted", f'<span class="eyebrow">SUPPLIER RESPONSE</span><h1>Quotation submitted successfully</h1><p class="muted">Thank you. Your quotation for <strong>{html_escape(invitation.rfq.rfq_number)}</strong> has been received by ProcurePilot.</p><div class="notice"><strong>Total quoted value:</strong> {currency} {total:,.2f}<br><strong>Delivery:</strong> {payload.delivery_days} days<br><strong>Valid until:</strong> {payload.valid_until.strftime("%d %b %Y")}</div>')
