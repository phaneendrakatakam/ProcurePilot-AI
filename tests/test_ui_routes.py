from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_login_page_is_served():
    response = client.get("/login")
    assert response.status_code == 200
    assert "ProcurePilot" in response.text
    assert "Sign in to ProcurePilot" in response.text


def test_application_shell_is_served():
    response = client.get("/app")
    assert response.status_code == 200
    assert "app-shell" in response.text
    assert "Role-aware" not in response.text or "ProcurePilot" in response.text


def test_static_assets_are_served():
    css = client.get("/static/css/app.css")
    js = client.get("/static/js/app.js")
    assert css.status_code == 200
    assert js.status_code == 200
    assert ".app-shell" in css.text
    assert "roleNavigation" in js.text


def test_receiving_routes_and_workspace_are_wired():
    js = (ROOT / "app/web/static/js/app.js").read_text(encoding="utf-8-sig")
    assert 'if (view === "deliveries") return renderExpectedDeliveries();' in js
    assert 'if (view === "receipts") return renderGoodsReceipts();' in js
    assert 'if (view === "goods-receipt-detail") return renderGoodsReceiptDetail(state.goodsReceiptId);' in js
    assert '/goods-receipts/expected-deliveries' in js
    assert 'Record receipt' in js
    assert 'Post receipt' in js
