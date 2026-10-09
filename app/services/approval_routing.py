from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identity import Role, User, UserRole
from app.models.procurement import PurchaseRequest, PurchaseRequestApproval


def _active_users_with_role(db: Session, role_code: str) -> list[User]:
    return db.scalars(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            Role.code == role_code,
            User.is_active.is_(True),
        )
        .order_by(User.full_name.asc(), User.id.asc())
    ).all()


def _department_manager(db: Session, request: PurchaseRequest) -> User | None:
    if request.department_id is None:
        return None

    return db.scalar(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            Role.code == "MANAGER",
            User.is_active.is_(True),
            User.department_id == request.department_id,
        )
        .order_by(User.full_name.asc(), User.id.asc())
    )


def route_purchase_request_approvals(
    db: Session,
    request: PurchaseRequest,
) -> list[PurchaseRequestApproval]:
    """Create the mandatory approval chain after supplier selection.

    Every employee purchase requires all configured approval roles in sequence:
    the request department Manager, Procurement Head, and Finance Manager.
    Purchase value does not determine whether approval is required. The amount
    remains available to approvers as commercial and budget context.
    """
    existing = db.scalars(
        select(PurchaseRequestApproval)
        .where(PurchaseRequestApproval.purchase_request_id == request.id)
        .order_by(PurchaseRequestApproval.sequence.asc())
    ).all()
    if existing:
        return existing

    manager = _department_manager(db, request)
    if manager is None:
        raise ValueError(
            "No active Manager is configured for the purchase request department"
        )

    procurement_heads = _active_users_with_role(db, "PROCUREMENT_HEAD")
    if not procurement_heads:
        raise ValueError(
            "No active Procurement Head is configured for approval"
        )

    finance_managers = _active_users_with_role(db, "FINANCE_MANAGER")
    if not finance_managers:
        raise ValueError(
            "No active Finance Manager is configured for approval"
        )

    approvers = [
        (manager, "MANAGER"),
        (procurement_heads[0], "PROCUREMENT_HEAD"),
        (finance_managers[0], "FINANCE_MANAGER"),
    ]

    approvals: list[PurchaseRequestApproval] = []
    for sequence, (user, role) in enumerate(approvers, start=1):
        approval = PurchaseRequestApproval(
            purchase_request_id=request.id,
            approver_user_id=user.id,
            approver_role=role,
            sequence=sequence,
            status="PENDING",
        )
        db.add(approval)
        approvals.append(approval)

    request.status = "PENDING_APPROVAL"
    return approvals
