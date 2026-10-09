from email.message import EmailMessage
import smtplib
import uuid

from app.core.config import settings


def build_rfq_email(*, to_email: str, supplier_name: str, rfq_number: str, request_title: str, response_deadline: str, response_url: str, item_lines: list[str], instructions: str | None) -> EmailMessage:
    if not settings.smtp_from_email:
        raise RuntimeError("SMTP sender email is not configured. Set SMTP_FROM_EMAIL before sending RFQs.")
    subject = f"RFQ {rfq_number} — quotation requested"
    items = "\n".join(f"• {line}" for line in item_lines)
    instruction_text = instructions or "Please provide your commercial quotation and delivery commitment."
    text = (f"Hello {supplier_name},\n\nProcurePilot is requesting a quotation for {request_title}.\n\n"
            f"RFQ: {rfq_number}\nResponse deadline: {response_deadline}\n\nRequested items:\n{items}\n\n"
            f"Instructions:\n{instruction_text}\n\nSubmit your quotation securely here:\n{response_url}\n\n"
            "This response link is unique to your invitation and expires at the response deadline.\n\nProcurePilot")
    html_items = "".join(f"<li>{line}</li>" for line in item_lines)
    html = f"""<!doctype html><html><body style="font-family:Arial,sans-serif;color:#102a43">
    <h2>ProcurePilot — Request for Quotation</h2><p>Hello {supplier_name},</p>
    <p>Please submit your quotation for <strong>{request_title}</strong>.</p>
    <p><strong>RFQ:</strong> {rfq_number}<br><strong>Response deadline:</strong> {response_deadline}</p>
    <h3>Requested items</h3><ul>{html_items}</ul><p><strong>Instructions</strong><br>{instruction_text}</p>
    <p><a href="{response_url}" style="display:inline-block;padding:12px 18px;background:#0f766e;color:#fff;text-decoration:none;border-radius:8px">Submit quotation</a></p>
    <p style="font-size:12px;color:#64748b">This secure invitation is unique to your supplier account and expires at the response deadline.</p></body></html>"""
    message = EmailMessage()
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = to_email
    message["Subject"] = subject
    message["Message-ID"] = f"<{uuid.uuid4().hex}@procurepilot.local>"
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    return message


def send_email(message: EmailMessage) -> None:
    if not settings.smtp_host or not settings.smtp_from_email:
        raise RuntimeError("SMTP email integration is not configured. Set SMTP_HOST and SMTP_FROM_EMAIL.")
    if settings.smtp_use_tls:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password or "")
            server.send_message(message)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password or "")
            server.send_message(message)


def build_purchase_order_email(
    *,
    to_email: str,
    supplier_name: str,
    po_number: str,
    request_title: str,
    currency: str,
    total_amount: str,
    subtotal: str,
    tax_amount: str,
    delivery_days: int,
    payment_terms_days: int,
    required_date: str | None,
    item_lines: list[str],
    notes: str | None,
) -> EmailMessage:
    """Build the supplier-facing notification sent when a PO is formally issued."""
    if not settings.smtp_from_email:
        raise RuntimeError(
            "SMTP sender email is not configured. Set SMTP_FROM_EMAIL before sending purchase orders."
        )

    from html import escape

    subject = f"Purchase Order {po_number} — issued"
    items = "\n".join(f"• {line}" for line in item_lines)
    required_text = required_date or "Not specified"
    notes_text = notes or "No additional purchasing notes."
    text = (
        f"Hello {supplier_name},\n\n"
        f"ProcurePilot has formally issued purchase order {po_number} for {request_title}.\n\n"
        f"Purchase Order: {po_number}\nRequired date: {required_text}\n"
        f"Delivery: {delivery_days} days\nPayment terms: {payment_terms_days} days\n\n"
        f"Commercial summary:\nSubtotal: {currency} {subtotal}\nTax: {currency} {tax_amount}\n"
        f"Total: {currency} {total_amount}\n\nItems:\n{items}\n\n"
        f"Purchasing notes:\n{notes_text}\n\nProcurePilot"
    )
    html_items = "".join(f"<li>{escape(line)}</li>" for line in item_lines)
    html = f"""<!doctype html><html><body style="font-family:Arial,sans-serif;color:#102a43">
<h2>ProcurePilot — Purchase Order Issued</h2>
<p>Hello {escape(supplier_name)},</p>
<p>ProcurePilot has formally issued purchase order <strong>{escape(po_number)}</strong> for <strong>{escape(request_title)}</strong>.</p>
<p><strong>Required date:</strong> {escape(required_text)}<br>
<strong>Delivery:</strong> {delivery_days} days<br><strong>Payment terms:</strong> {payment_terms_days} days</p>
<h3>Commercial summary</h3>
<p><strong>Subtotal:</strong> {escape(currency)} {escape(subtotal)}<br>
<strong>Tax:</strong> {escape(currency)} {escape(tax_amount)}<br>
<strong>Total:</strong> <strong>{escape(currency)} {escape(total_amount)}</strong></p>
<h3>Items</h3><ul>{html_items}</ul>
<h3>Purchasing notes</h3><p>{escape(notes_text)}</p>
<p style="font-size:12px;color:#64748b">This email confirms that the purchase order has been formally issued by ProcurePilot.</p>
</body></html>"""
    message = EmailMessage()
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = to_email
    message["Subject"] = subject
    message["Message-ID"] = f"<{uuid.uuid4().hex}@procurepilot.local>"
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    return message


def build_automation_email(*, to_email: str, subject: str, body: str) -> EmailMessage:
    """Build a plain-text operational reminder generated by notification automation."""
    if not settings.smtp_from_email:
        raise RuntimeError("SMTP sender email is not configured. Set SMTP_FROM_EMAIL before sending automation notifications.")
    message = EmailMessage()
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = to_email
    message["Subject"] = subject
    message["Message-ID"] = f"<{uuid.uuid4().hex}@procurepilot.local>"
    message.set_content(body)
    return message
