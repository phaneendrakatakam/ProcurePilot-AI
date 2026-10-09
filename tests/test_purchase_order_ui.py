from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_purchase_order_workspace_is_wired():
    js = (ROOT / "app/web/static/js/app.js").read_text(encoding="utf-8")
    html = (ROOT / "app/web/app.html").read_text(encoding="utf-8")
    css = (ROOT / "app/web/static/css/purchase-order.css").read_text(encoding="utf-8")
    assert '"purchase-orders"' in js
    assert 'function renderPurchaseOrders()' in js
    assert 'function renderPurchaseOrderDetail(poId)' in js
    assert 'api("/purchase-orders")' in js
    assert 'api("/supplier-selections")' in js
    assert 'data-create-po' in js
    assert 'api("/purchase-orders", { method: "POST"' in js
    assert 'Purchase Orders' in js
    assert 'purchase-order.css?v=20260924-purchase-order-po' in html
    assert '.po-detail-grid' in css

def test_purchase_order_workspace_uses_approved_selection_gate():
    js = (ROOT / "app/web/static/js/app.js").read_text(encoding="utf-8")
    assert 'requestMap[s.request_id]?.status === "APPROVED"' in js
    assert 'This purchase request is not approved' in js
