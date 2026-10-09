from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def test_payment_finalization_route_is_finance_only():
    route = (ROOT / "app/api/routes/invoice_matching.py").read_text(encoding="utf-8")
    assert 'require_permissions("finance.review")' in route
    assert 'finalize-payment' in route
    assert 'invoice.status != "READY_FOR_PAYMENT"' in route
    assert 'invoice.status = "PAID"' in route

def test_invoice_has_payment_finalization_fields():
    model = (ROOT / "app/models/invoices.py").read_text(encoding="utf-8")
    assert "payment_reference" in model
    assert "paid_at" in model
    assert "paid_by_user_id" in model

def test_ui_exposes_finance_finalization():
    js = (ROOT / "app/web/static/js/app.js").read_text(encoding="utf-8")
    assert 'renderPaymentFinalization' in js
    assert '/invoice-matching/${invoiceId}/finalize-payment' in js
