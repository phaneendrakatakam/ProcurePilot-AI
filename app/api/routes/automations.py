from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_permissions
from app.core.database import get_db
from app.models.notifications import Notification
from app.models.identity import User
from app.services.automation import run_automations

router = APIRouter(prefix="", tags=["automation"])


@router.get("/notifications")
def list_notifications(
    unread_only: bool = Query(False),
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Notification)
        .where(Notification.recipient_user_id == actor.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    rows = db.scalars(stmt).all()
    return [
        {
            "id": row.id,
            "notification_type": row.notification_type,
            "subject": row.subject,
            "body": row.body,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "status": row.status,
            "created_at": row.created_at,
            "sent_at": row.sent_at,
            "read_at": row.read_at,
        }
        for row in rows
    ]


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_user_id == actor.id,
        )
    )
    if row:
        row.read_at = datetime.now(timezone.utc)
        db.commit()
    return {"status": "ok"}


@router.post("/automations/run")
def run_automation_cycle(
    dry_run: bool = Query(False),
    actor: User = Depends(require_permissions("automation.run")),
    db: Session = Depends(get_db),
):
    return run_automations(db, dry_run=dry_run)
