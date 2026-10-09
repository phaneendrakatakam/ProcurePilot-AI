from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_sourcing_queue_and_transition_are_implemented():
    route = (ROOT / "app/api/routes/purchase_requests.py").read_text()
    js = (ROOT / "app/web/static/js/app.js").read_text(encoding="utf-8")

    assert "def list_sourcing_queue" in route
    assert 'Depends(require_permissions("sourcing.manage"))' in route
    assert "def start_sourcing" in route
    assert 'request.status = "SOURCING"' in route
    assert "PURCHASE_REQUEST_SOURCING_STARTED" in route
    assert "/purchase-requests/sourcing/queue" in js
    assert "Start sourcing" in js
    assert "Sourcing Workspace" in js