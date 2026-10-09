from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_purchase_order_ui_preserves_payment_terms_and_renders_human_readable_specs():
    js = (ROOT / "app/web/static/js/app.js").read_text(encoding="utf-8")
    route = (ROOT / "app/api/routes/purchase_orders.py").read_text(encoding="utf-8")

    assert "Number.parseInt(String(fd.get(\"payment_terms_days\")" in js
    assert "payment_terms_days: paymentTermsDays" in js
    assert "toast(`${po.po_number} created as draft · ${po.payment_terms_days} day payment terms.`)" in js
    assert "payment_terms_days = int(payload.payment_terms_days)" in route
    assert "payment_terms_days=payment_terms_days" in route
    assert "item.specifications.notes || Object.entries(item.specifications)" in js
    assert "JSON.stringify(item.specifications)" not in js
