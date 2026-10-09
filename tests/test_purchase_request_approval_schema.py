from datetime import datetime
import uuid

from app.schemas.purchase_request_approvals import ApprovalDecisionResponse, PendingApprovalSummary


def test_pending_approval_response_allows_undecided_timestamp():
    response = ApprovalDecisionResponse(
        approval_id=uuid.uuid4(),
        purchase_request_id=uuid.uuid4(),
        request_number="PR-TEST-0001",
        approval_sequence=1,
        approver_role="FINANCE_MANAGER",
        decision="PENDING",
        approval_status="PENDING",
        request_status="PENDING_APPROVAL",
        decision_comment=None,
        decided_at=None,
    )
    assert response.decided_at is None


def test_pending_approval_summary_schema_is_preserved():
    summary = PendingApprovalSummary(
        approval_id=uuid.uuid4(),
        purchase_request_id=uuid.uuid4(),
        request_number="PR-TEST-0001",
        title="Office monitors",
        category="IT Equipment",
        requester_name="Test Employee",
        department_name="Engineering",
        estimated_total=240000.0,
        currency="INR",
        approval_sequence=3,
        total_approval_steps=3,
        approver_role="FINANCE_MANAGER",
        status="PENDING",
        created_at=datetime.now(),
    )
    assert summary.approver_role == "FINANCE_MANAGER"
