from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_supplier_email_quotation_flow_is_wired():
    rfq = (ROOT / "app/api/routes/rfqs.py").read_text(encoding="utf-8")
    response = (ROOT / "app/api/routes/supplier_responses.py").read_text(encoding="utf-8")
    model = (ROOT / "app/models/procurement.py").read_text(encoding="utf-8")
    config = (ROOT / "app/core/config.py").read_text(encoding="utf-8")
    router = (ROOT / "app/api/router.py").read_text(encoding="utf-8")
    js = (ROOT / "app/web/static/js/app.js").read_text(encoding="utf-8")
    html = (ROOT / "app/web/app.html").read_text(encoding="utf-8")
    assert "send_email(message)" in rfq
    assert "response_token_hash" in rfq
    assert 'prefix="/supplier-responses"' in response
    assert "SUPPLIER_PORTAL" in response
    assert "submission_source" in model
    assert "smtp_host" in config
    assert "supplier_responses_router" in router
    assert "Record quotation" not in js
    assert "secure quotation link" in js
    assert "/static/js/app.js?v=" in html


def test_supplier_email_migration_is_chained_after_approvals():
    migration = (ROOT / "alembic/versions/3a8f6e2b1c40_supplier_email_quotation_portal.py").read_text(encoding="utf-8")
    assert 'down_revision = "2f7c1a9e6b40"' in migration
    assert '"response_token_hash"' in migration
    assert '"submission_source"' in migration
