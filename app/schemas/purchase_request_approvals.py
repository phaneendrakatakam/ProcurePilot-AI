import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ApprovalDecisionCreate(BaseModel):
    decision: str = Field(pattern="^(APPROVE|REJECT)$")
    comment: str | None = Field(default=None, max_length=2000)


class ApprovalDecisionResponse(BaseModel):
    approval_id: uuid.UUID
    purchase_request_id: uuid.UUID
    request_number: str
    approval_sequence: int
    approver_role: str
    decision: str
    approval_status: str
    request_status: str
    decision_comment: str | None
    decided_at: datetime | None = None


class PendingApprovalSummary(BaseModel):
    approval_id: uuid.UUID
    purchase_request_id: uuid.UUID
    request_number: str
    title: str
    category: str | None
    requester_name: str
    department_name: str | None
    estimated_total: float | None
    currency: str | None
    approval_sequence: int
    total_approval_steps: int
    approver_role: str
    status: str
    created_at: datetime
