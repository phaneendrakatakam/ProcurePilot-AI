from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_purchase_order_creation_api_is_wired():
    route = (ROOT / "app/api/routes/purchase_orders.py").read_text(encoding="utf-8")
    schema = (ROOT / "app/schemas/purchase_orders.py").read_text(encoding="utf-8")
    router = (ROOT / "app/api/router.py").read_text(encoding="utf-8")
    assert 'prefix="/purchase-orders"' in route
    assert "def create_purchase_order" in route
    assert 'require_permissions("sourcing.manage")' in route
    assert 'request.status != "APPROVED"' in route
    assert "All mandatory approval steps must be approved" in route
    assert "supplier_selection_id" in route
    assert "A purchase order already exists for this supplier selection" in route
    assert 'event_type="PURCHASE_ORDER_CREATED"' in route
    assert 'action="PURCHASE_ORDER_CREATED"' in route
    assert "class PurchaseOrderCreate" in schema
    assert "class PurchaseOrderDetail" in schema
    assert "purchase_orders_router" in router
    assert "api_router.include_router(purchase_orders_router)" in router

def test_purchase_order_creation_uses_selected_supplier_quotation():
    route = (ROOT / "app/api/routes/purchase_orders.py").read_text(encoding="utf-8")
    assert "selection.quotation" in route
    assert "quotation.total_amount" in route
    assert "quotation.currency" in route
    assert "quotation.delivery_days" in route
