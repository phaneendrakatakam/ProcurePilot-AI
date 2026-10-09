from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mandatory_approval_routing_has_no_value_threshold():
    route = (ROOT / "app/services/approval_routing.py").read_text(encoding="utf-8")

    assert "Purchase value does not determine whether approval is required" in route
    assert 'Role.code == "MANAGER"' in route
    assert '"PROCUREMENT_HEAD"' in route
    assert '"FINANCE_MANAGER"' in route
    assert "HIGH_VALUE_THRESHOLD" not in route


def test_mandatory_approval_routing_requires_all_three_approvers():
    route = (ROOT / "app/services/approval_routing.py").read_text(encoding="utf-8")

    assert 'No active Manager is configured' in route
    assert 'No active Procurement Head is configured' in route
    assert 'No active Finance Manager is configured' in route
    assert '(manager, "MANAGER")' in route
    assert '(procurement_heads[0], "PROCUREMENT_HEAD")' in route
    assert '(finance_managers[0], "FINANCE_MANAGER")' in route


def test_supplier_selection_triggers_approval_routing():
    route = (ROOT / "app/api/routes/supplier_selections.py").read_text(encoding="utf-8")
    service = (ROOT / "app/services/approval_routing.py").read_text(encoding="utf-8")

    assert "route_purchase_request_approvals" in route
    assert 'request.status = "PENDING_APPROVAL"' in service
    assert "APPROVALS_ROUTED" in route
    assert 'action="APPROVAL_CREATED"' in route
