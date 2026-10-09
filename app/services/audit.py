import uuid

from sqlalchemy.orm import Session

from app.models.governance import ActorType, AuditLog


def record_audit_event(
    db: Session,
    *,
    actor_type: ActorType,
    action: str,
    entity_type: str,
    entity_id: str,
    actor_user_id: uuid.UUID | None = None,
    details: dict | None = None,
) -> AuditLog:
    """Append a meaningful business/governance event to the audit history."""
    event = AuditLog(
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    db.add(event)
    return event
