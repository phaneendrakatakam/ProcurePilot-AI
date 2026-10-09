from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_goods_receipt_model_schema_and_permission_are_defined():
    model = (ROOT / "app/models/goods_receipts.py").read_text(encoding="utf-8")
    schema = (ROOT / "app/schemas/goods_receipts.py").read_text(encoding="utf-8")
    route = (ROOT / "app/api/routes/goods_receipts.py").read_text(encoding="utf-8")

    assert '__tablename__ = "goods_receipts"' in model
    assert '__tablename__ = "goods_receipt_items"' in model
    assert 'purchase_order_id' in model
    assert 'purchase_order_item_id' in model
    assert 'ck_goods_receipt_quantity_split' in model
    assert 'goods_receipts.manage' in route
    assert 'class GoodsReceiptCreate' in schema
    assert 'class GoodsReceiptDetail' in schema


def test_goods_receipt_lifecycle_and_partial_receipt_rules_are_wired():
    route = (ROOT / "app/api/routes/goods_receipts.py").read_text(encoding="utf-8")
    assert '@router.post("", response_model=GoodsReceiptDetail, status_code=status.HTTP_201_CREATED)' in route
    assert '@router.post("/{receipt_id}/post", response_model=GoodsReceiptDetail)' in route
    assert 'po.status != "ISSUED"' in route
    assert 'status="DRAFT"' in route
    assert 'receipt.status = "POSTED"' in route
    assert 'GOODS_RECEIPT_CREATED' in route
    assert 'GOODS_RECEIPT_POSTED' in route
    assert 'exceeds the remaining quantity' in route


def test_goods_receipt_receiving_queue_and_workspace_are_wired():
    route = (ROOT / "app/api/routes/goods_receipts.py").read_text(encoding="utf-8")
    schema = (ROOT / "app/schemas/goods_receipts.py").read_text(encoding="utf-8")
    js = (ROOT / "app/web/static/js/app.js").read_text(encoding="utf-8-sig")
    css = (ROOT / "app/web/static/css/app.css").read_text(encoding="utf-8")

    assert '@router.get("/eligible-orders", response_model=list[GoodsReceiptOpenPurchaseOrder])' in route
    assert 'PurchaseOrder.status == "ISSUED"' in route
    assert 'remaining_quantity=remaining' in route
    assert 'class GoodsReceiptOpenPurchaseOrder' in schema
    assert 'api("/goods-receipts/eligible-orders")' in js
    assert 'function renderExpectedDeliveries()' in js
    assert 'function renderGoodsReceipts()' in js
    assert 'function renderGoodsReceiptDetail' in js
    assert 'Post goods receipt' in js
    assert 'Accepted + rejected quantity must equal received quantity' in js
    assert '.receiving-line' in css


def test_goods_receipt_receiving_status_history_and_read_visibility_are_wired():
    route = (ROOT / "app/api/routes/goods_receipts.py").read_text(encoding="utf-8")
    schema = (ROOT / "app/schemas/goods_receipts.py").read_text(encoding="utf-8")
    js = (ROOT / "app/web/static/js/app.js").read_text(encoding="utf-8")
    css = (ROOT / "app/web/static/css/app.css").read_text(encoding="utf-8")

    assert 'def _receiving_status(' in route
    assert '"EXPECTED"' in route
    assert '"PARTIALLY_RECEIVED"' in route
    assert '"FULLY_RECEIVED"' in route
    assert 'PURCHASE_ORDER_RECEIVING_STATUS_CHANGED' in route
    assert '@router.get("/purchase-orders/{purchase_order_id}/history"' in route
    assert 'require_any_permissions("goods_receipts.manage", "sourcing.manage")' in route
    assert 'receiving_status: str' in schema
    assert 'function receivingStatusPill' in js
    assert 'data-delivery-search' in js
    assert 'data-delivery-status' in js
    assert 'data-receipt-search' in js
    assert 'data-receipt-status-filter' in js
    assert 'Receipt history' in js
    assert '.receiving-toolbar' in css


def test_goods_receipt_status_transition_audit_is_guarded_and_traceable():
    route = (ROOT / "app/api/routes/goods_receipts.py").read_text(encoding="utf-8")
    assert 'previous_receiving_status = _receiving_status(db, po)' in route
    assert 'if previous_receiving_status != receiving_status:' in route
    assert '"from_status": previous_receiving_status' in route
    assert '"to_status": receiving_status' in route


def test_goods_receipt_receiving_permissions_and_quantity_guards_are_explicit():
    route = (ROOT / "app/api/routes/goods_receipts.py").read_text(encoding="utf-8")
    schema = (ROOT / "app/schemas/goods_receipts.py").read_text(encoding="utf-8")
    assert 'require_any_permissions("goods_receipts.manage", "sourcing.manage")' in route
    assert 'actor: User = Depends(require_permissions("goods_receipts.manage"))' in route
    assert 'line.received_quantity > remaining' in route
    assert 'Decimal(line.received_quantity) > remaining' in route
    assert 'rejected_quantity > 0 and not (self.rejection_reason or "").strip()' in schema
    assert 'self.accepted_quantity + self.rejected_quantity != self.received_quantity' in schema
