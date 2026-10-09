from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_permissions
from app.core.database import get_db
from app.models.governance import ActorType, AuditLog
from app.models.identity import User
from app.schemas.admin import AuditLogResponse

router = APIRouter(prefix="/admin/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditLogResponse])
def list_audit_logs(
    actor_type: ActorType | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    _: User = Depends(require_permissions("users.read")),
    db: Session = Depends(get_db),
):
    stmt = select(AuditLog)
    if actor_type is not None:
        stmt = stmt.where(AuditLog.actor_type == actor_type)
    if action:
        stmt = stmt.where(AuditLog.action == action.strip())
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type.strip())
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit)

    rows = db.scalars(stmt).all()
    actor_ids = {row.actor_user_id for row in rows if row.actor_user_id}
    actor_names = {
        user.id: user.full_name for user in db.scalars(select(User).where(User.id.in_(actor_ids))).all()
    } if actor_ids else {}
    return [
        AuditLogResponse(
            id=row.id,
            actor_type=row.actor_type.value,
            actor_user_id=row.actor_user_id,
            actor_user_name=actor_names.get(row.actor_user_id),
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            details=row.details,
            created_at=row.created_at,
        )
        for row in rows
    ]
