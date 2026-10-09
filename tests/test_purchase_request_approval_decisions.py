from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_approval_decision_api_is_implemented():
    route = (ROOT / "app/api/routes/purchase_request_approvals.py").read_text(encoding="utf-8")
    schema = (ROOT / "app/schemas/purchase_request_approvals.py").read_text(encoding="utf-8")
    router = (ROOT / "app/api/router.py").read_text(encoding="utf-8")

    assert 'prefix="/purchase-request-approvals"' in route
    assert '"/{approval_id}/decision"' in route
    assert "def decide_purchase_request_approval" in route
    assert 'require_permissions("approvals.decide")' in route
    assert "Only the assigned approver can decide" in route
    assert "Earlier approval steps must be completed first" in route
    assert "A rejection comment must be at least 10 characters" in route
    assert 'event_type="APPROVAL_APPROVED"' in route
    assert 'event_type="APPROVAL_REJECTED"' in route
    assert 'action="APPROVAL_APPROVED"' in route
    assert 'action="APPROVAL_REJECTED"' in route
    assert 'request.status = "APPROVED"' in route
    assert 'request.status = "REJECTED"' in route
    assert "class ApprovalDecisionCreate" in schema
    assert "class ApprovalDecisionResponse" in schema
    assert "purchase_request_approvals_router" in router


def test_approval_decision_api_enforces_sequential_human_decisions():
    route = (ROOT / "app/api/routes/purchase_request_approvals.py").read_text(encoding="utf-8")
    assert 'approval.status != "PENDING"' in route
    assert "approval.approver_user_id != actor.id" in route
    assert "first_pending" in route
    assert "first_pending.id != approval.id" in route


def test_approval_detail_api_is_implemented():
    route = (ROOT / "app/api/routes/purchase_request_approvals.py").read_text(encoding="utf-8")
    assert '@router.get("/{approval_id}", response_model=ApprovalDecisionResponse)' in route
    assert 'Only the assigned approver can view this approval step' in route
    assert 'def get_purchase_request_approval' in route
