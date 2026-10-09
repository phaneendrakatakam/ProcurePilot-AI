from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def test_command_center_route_is_wired():
    route = (ROOT / "app/api/routes/dashboard.py").read_text(encoding="utf-8")
    router = (ROOT / "app/api/router.py").read_text(encoding="utf-8")
    schema = (ROOT / "app/schemas/dashboard.py").read_text(encoding="utf-8")
    assert 'router = APIRouter(prefix="/dashboard"' in route
    assert '@router.get(""' in route
    assert 'get_current_user' in route
    assert 'api_router.include_router(dashboard_router)' in router
    assert 'class DashboardKPIs' in schema
    assert 'class DashboardResponse' in schema


def test_command_center_requires_authentication():
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 401


def test_command_center_ui_is_role_aware():
    js = (ROOT / "app/web/static/js/app.js").read_text(encoding="utf-8-sig")
    assert 'api("/dashboard")' in js
    assert 'Procurement Command Center' in js
    assert 'My Procurement Command Center' in js
    assert 'Finance Control Center' in js
    assert 'Receiving Command Center' in js
    for key in ["open_requests", "pending_approvals", "rfqs_awaiting_response", "pos_awaiting_issue", "expected_deliveries", "partial_receipts", "invoice_exceptions", "three_way_match_exceptions", "spend"]:
        assert key in js
