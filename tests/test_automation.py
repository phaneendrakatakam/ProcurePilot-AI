from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_automation_automation_service_has_all_required_rules():
    service = (ROOT / "app/services/automation.py").read_text(encoding="utf-8")
    for rule in ("RFQ_RESPONSE_REMINDER", "DELIVERY_APPROACHING", "INVOICE_EXCEPTION", "APPROVAL_PENDING_REMINDER"):
        assert rule in service
    assert "def run_automations" in service
    assert "dedupe_key" in service
    assert "dry_run" in service


def test_automation_notification_model_and_migration_are_idempotent_ready():
    model = (ROOT / "app/models/notifications.py").read_text(encoding="utf-8")
    migration = next(ROOT.glob("alembic/versions/b1c4d6e8f902_*.py")).read_text(encoding="utf-8")
    assert 'class Notification' in model
    assert 'UniqueConstraint("dedupe_key"' in model
    assert 'Revision ID: b1c4d6e8f902' in migration
    assert 'Revises: a7e4c2d9f610' in migration


def test_automation_routes_and_scheduler_entrypoint_are_wired():
    router = (ROOT / "app/api/router.py").read_text(encoding="utf-8")
    route = (ROOT / "app/api/routes/automations.py").read_text(encoding="utf-8")
    script = (ROOT / "scripts/run_automations.py").read_text(encoding="utf-8")
    assert 'from app.api.routes.automations import router as automations_router' in router
    assert 'api_router.include_router(automations_router)' in router
    assert '"/automations/run"' in route
    assert '"/notifications"' in route
    assert 'run_automations(db)' in script


def test_automation_automation_is_admin_permission_seeded():
    seed = (ROOT / "app/seed/bootstrap.py").read_text(encoding="utf-8")
    assert '"automation.run"' in seed
    assert '"ADMINISTRATOR": {code for code, _, _ in PERMISSION_SEEDS}' in seed


def test_automation_notification_center_is_wired_to_existing_bell():
    js = (ROOT / "app/web/static/js/app.js").read_text(encoding="utf-8-sig")
    css = (ROOT / "app/web/static/css/app.css").read_text(encoding="utf-8")
    assert '/notifications?unread_only=true' in js
    assert 'api("/notifications")' in js or 'api(`/notifications`' in js
    assert 'data-mark-notification' in js
    assert 'notification-list' in css
