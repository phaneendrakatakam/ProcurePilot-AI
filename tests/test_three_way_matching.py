from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_three_way_matching_model_and_migration_are_defined():
    model = (ROOT / "app/models/invoice_matching.py").read_text(encoding="utf-8")
    migration = (ROOT / "alembic/versions/a7e4c2d9f610_add_supplier_invoice_matching.py").read_text(encoding="utf-8")
    assert '__tablename__ = "supplier_invoice_matches"' in model
    assert 'UniqueConstraint("invoice_id"' in model
    assert 'line_results' in model
    assert 'supplier_invoice_matches' in migration
    assert 'down_revision = "9c6e1f4a2b70"' in migration


def test_three_way_matching_engine_checks_po_receipt_and_invoice():
    route = (ROOT / "app/api/routes/invoice_matching.py").read_text(encoding="utf-8")
    assert '@router.post("/{invoice_id}/run"' in route
    assert 'GoodsReceipt.status == "POSTED"' in route
    assert 'accepted_quantity' in route
    assert 'po_unit_price' in route
    assert 'invoice_unit_price' in route
    assert 'quantity_variance' in route
    assert 'price_variance_percent' in route
    assert 'MATCHED' in route
    assert 'EXCEPTION' in route


def test_three_way_matching_tolerance_is_configurable():
    config = (ROOT / "app/core/config.py").read_text(encoding="utf-8")
    env = (ROOT / ".env.example").read_text(encoding="utf-8")
    route = (ROOT / "app/api/routes/invoice_matching.py").read_text(encoding="utf-8")
    assert 'match_quantity_tolerance' in config
    assert 'match_price_tolerance_percent' in config
    assert 'MATCH_QUANTITY_TOLERANCE' in env
    assert 'MATCH_PRICE_TOLERANCE_PERCENT' in env
    assert 'settings.match_quantity_tolerance' in route
    assert 'settings.match_price_tolerance_percent' in route


def test_three_way_matching_invoice_state_transitions_are_wired():
    route = (ROOT / "app/api/routes/invoice_matching.py").read_text(encoding="utf-8")
    assert 'invoice.status = "READY_FOR_PAYMENT" if match.result == "MATCHED" else "EXCEPTION"' in route
    assert 'SUPPLIER_INVOICE_MATCHED' in route
    assert 'SUPPLIER_INVOICE_MATCH_EXCEPTION' in route


def test_three_way_matching_api_is_registered():
    router = (ROOT / "app/api/router.py").read_text(encoding="utf-8")
    assert 'from app.api.routes.invoice_matching import router as invoice_matching_router' in router
    assert 'api_router.include_router(invoice_matching_router)' in router


def test_three_way_matching_workspace_is_live():
    js = (ROOT / "app/web/static/js/app.js").read_text(encoding="utf-8-sig")
    css = (ROOT / "app/web/static/css/app.css").read_text(encoding="utf-8")
    assert 'function renderThreeWayMatching()' in js
    assert 'function renderThreeWayMatchingDetail' in js
    assert 'api("/invoice-matching")' in js
    assert 'Run 3-way match' in js
    assert 'Purchase Order' in js
    assert 'Goods Receipt' in js
    assert 'SUPPLIER INVOICE' in js
    assert '.match-three-column' in css
    assert '.match-check' in css


def test_three_way_matching_uses_existing_invoice_handoff():
    js = (ROOT / "app/web/static/js/app.js").read_text(encoding="utf-8-sig")
    assert 'state.matchingInvoiceId' in js
    assert 'navigate("matching-detail")' in js
    assert 'view === "matching"' in js
    assert 'view === "matching-detail"' in js


def test_three_way_matching_result_exposes_variance_and_line_evidence():
    schema = (ROOT / "app/schemas/invoice_matching.py").read_text(encoding="utf-8")
    route = (ROOT / "app/api/routes/invoice_matching.py").read_text(encoding="utf-8")
    assert 'class InvoiceMatchResponse' in schema
    assert 'class InvoiceMatchLine' in schema
    for field in ['quantity_variance', 'price_variance', 'exception_reason', 'line_results']:
        assert field in schema
        assert field in route
