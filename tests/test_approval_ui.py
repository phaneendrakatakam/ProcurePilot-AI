from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_approval_ui_and_pending_queue_are_implemented():
    js=(ROOT/"app/web/static/js/app.js").read_text(encoding="utf-8")
    html=(ROOT/"app/web/app.html").read_text(encoding="utf-8")
    route=(ROOT/"app/api/routes/purchase_request_approvals.py").read_text(encoding="utf-8")
    schema=(ROOT/"app/schemas/purchase_request_approvals.py").read_text(encoding="utf-8")
    assert "renderApprovals" in js
    assert "renderApprovalDetail" in js
    assert "/purchase-request-approvals/pending" in js
    assert "data-decision=\"APPROVE\"" in js
    assert "data-decision=\"REJECT\"" in js
    assert "approval-workspace.css" in html
    assert '/static/js/app.js?v=' in html
    assert '@router.get("/pending"' in route
    assert "PendingApprovalSummary" in schema
