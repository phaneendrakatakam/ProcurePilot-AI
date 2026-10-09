import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies.auth import require_permissions
from app.core.database import get_db
from app.models.governance import ActorType
from app.models.identity import User
from app.models.procurement import PurchaseRequestApproval
from app.schemas.purchase_request_approvals import ApprovalDecisionCreate, ApprovalDecisionResponse, PendingApprovalSummary
from app.services.audit import record_audit_event
from app.services.purchase_requests import append_request_event

router = APIRouter(prefix="/purchase-request-approvals", tags=["purchase-request-approvals"])


@router.get("/pending", response_model=list[PendingApprovalSummary])
def list_pending_purchase_request_approvals(
    actor: User = Depends(require_permissions("approvals.decide")),
    db: Session = Depends(get_db),
) -> list[PendingApprovalSummary]:
    """Return the current user's actionable, in-sequence approval steps."""
    approvals = db.scalars(
        select(PurchaseRequestApproval)
        .options(selectinload(PurchaseRequestApproval.request))
        .where(
            PurchaseRequestApproval.approver_user_id == actor.id,
            PurchaseRequestApproval.status == "PENDING",
        )
        .order_by(PurchaseRequestApproval.created_at.desc(), PurchaseRequestApproval.sequence.asc())
    ).all()
    result = []
    for approval in approvals:
        request = approval.request
        if request.status != "PENDING_APPROVAL":
            continue
        # Only the first pending sequence is actionable. Later steps remain visible as upcoming.
        first_pending = db.scalar(
            select(PurchaseRequestApproval)
            .where(
                PurchaseRequestApproval.purchase_request_id == request.id,
                PurchaseRequestApproval.status == "PENDING",
            )
            .order_by(PurchaseRequestApproval.sequence.asc())
        )
        if not first_pending or first_pending.id != approval.id:
            continue
        total_steps = len(request.approvals)
        result.append(PendingApprovalSummary(
            approval_id=approval.id,
            purchase_request_id=request.id,
            request_number=request.request_number,
            title=request.title,
            category=request.category,
            requester_name=request.requester.full_name if request.requester else "Unknown requester",
            department_name=request.department.name if request.department else None,
            estimated_total=float(request.estimated_total) if request.estimated_total is not None else None,
            currency=request.currency,
            approval_sequence=approval.sequence,
            total_approval_steps=total_steps,
            approver_role=approval.approver_role,
            status=approval.status,
            created_at=approval.created_at,
        ))
    return result


@router.get("/{approval_id}", response_model=ApprovalDecisionResponse)
def get_purchase_request_approval(
    approval_id: uuid.UUID,
    actor: User = Depends(require_permissions("approvals.decide")),
    db: Session = Depends(get_db),
) -> ApprovalDecisionResponse:
    """Return one approval step for the assigned approver's review screen."""
    approval = db.scalar(
        select(PurchaseRequestApproval)
        .options(selectinload(PurchaseRequestApproval.request))
        .where(PurchaseRequestApproval.id == approval_id)
    )
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval step not found")
    if approval.approver_user_id != actor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned approver can view this approval step",
        )

    request = approval.request
    return ApprovalDecisionResponse(
        approval_id=approval.id,
        purchase_request_id=request.id,
        request_number=request.request_number,
        approval_sequence=approval.sequence,
        approver_role=approval.approver_role,
        decision=approval.status if approval.status != "PENDING" else "PENDING",
        approval_status=approval.status,
        request_status=request.status,
        decision_comment=approval.decision_comment,
        decided_at=approval.decided_at,
    )


@router.post("/{approval_id}/decision", response_model=ApprovalDecisionResponse)
def decide_purchase_request_approval(
    approval_id: uuid.UUID,
    payload: ApprovalDecisionCreate,
    actor: User = Depends(require_permissions("approvals.decide")),
    db: Session = Depends(get_db),
) -> ApprovalDecisionResponse:
    approval = db.scalar(
        select(PurchaseRequestApproval)
        .options(selectinload(PurchaseRequestApproval.request))
        .where(PurchaseRequestApproval.id == approval_id)
    )
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval step not found")

    request = approval.request
    if request.status != "PENDING_APPROVAL":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This purchase request is not awaiting approval (current status: {request.status})",
        )
    if approval.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This approval step has already been decided")
    if approval.approver_user_id != actor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the assigned approver can decide this approval step")

    first_pending = db.scalar(
        select(PurchaseRequestApproval)
        .where(
            PurchaseRequestApproval.purchase_request_id == request.id,
            PurchaseRequestApproval.status == "PENDING",
        )
        .order_by(PurchaseRequestApproval.sequence.asc())
    )
    if not first_pending or first_pending.id != approval.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Earlier approval steps must be completed first")

    decision = payload.decision.upper()
    comment = payload.comment.strip() if payload.comment else None
    if decision == "REJECT" and (not comment or len(comment) < 10):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A rejection comment must be at least 10 characters")

    now = datetime.now(timezone.utc)
    approval.status = "APPROVED" if decision == "APPROVE" else "REJECTED"
    approval.decision_comment = comment
    approval.decided_at = now

    if decision == "REJECT":
        previous_status = request.status
        request.status = "REJECTED"
        append_request_event(
            request,
            actor_type="HUMAN",
            actor_user_id=actor.id,
            event_type="APPROVAL_REJECTED",
            from_status=previous_status,
            to_status="REJECTED",
            details={
                "approval_id": str(approval.id),
                "sequence": approval.sequence,
                "approver_role": approval.approver_role,
                "comment": comment,
            },
        )
        record_audit_event(
            db,
            actor_type=ActorType.HUMAN,
            actor_user_id=actor.id,
            action="APPROVAL_REJECTED",
            entity_type="purchase_request_approval",
            entity_id=str(approval.id),
            details={
                "request_number": request.request_number,
                "sequence": approval.sequence,
                "approver_role": approval.approver_role,
                "comment": comment,
            },
        )
    else:
        next_pending = db.scalar(
            select(PurchaseRequestApproval)
            .where(
                PurchaseRequestApproval.purchase_request_id == request.id,
                PurchaseRequestApproval.status == "PENDING",
                PurchaseRequestApproval.sequence > approval.sequence,
            )
            .order_by(PurchaseRequestApproval.sequence.asc())
        )
        previous_status = request.status
        if next_pending is None:
            request.status = "APPROVED"
        append_request_event(
            request,
            actor_type="HUMAN",
            actor_user_id=actor.id,
            event_type="APPROVAL_APPROVED",
            from_status=previous_status,
            to_status=request.status,
            details={
                "approval_id": str(approval.id),
                "sequence": approval.sequence,
                "approver_role": approval.approver_role,
                "next_approval_id": str(next_pending.id) if next_pending else None,
                "comment": comment,
            },
        )
        record_audit_event(
            db,
            actor_type=ActorType.HUMAN,
            actor_user_id=actor.id,
            action="APPROVAL_APPROVED",
            entity_type="purchase_request_approval",
            entity_id=str(approval.id),
            details={
                "request_number": request.request_number,
                "sequence": approval.sequence,
                "approver_role": approval.approver_role,
                "next_approval_id": str(next_pending.id) if next_pending else None,
                "comment": comment,
            },
        )

    db.commit()
    return ApprovalDecisionResponse(
        approval_id=approval.id,
        purchase_request_id=request.id,
        request_number=request.request_number,
        approval_sequence=approval.sequence,
        approver_role=approval.approver_role,
        decision=decision,
        approval_status=approval.status,
        request_status=request.status,
        decision_comment=approval.decision_comment,
        decided_at=approval.decided_at,
    )
