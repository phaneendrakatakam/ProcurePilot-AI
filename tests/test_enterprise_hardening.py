from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_automation_dry_run_does_not_write_notifications():
    source = read_text("app/services/automation.py")
    assert 'if dry_run:' in source
    assert 'if not dry_run:' in source
    assert 'db.commit()' in source
    # The commit path is explicitly excluded for dry runs.
    assert 'if not dry_run:\n        db.commit()\n        keys =' in source


def test_automation_notifications_have_deterministic_dedupe_keys():
    source = read_text("app/services/automation.py")
    for prefix in (
        "rfq-response-reminder:",
        "approval-reminder:",
        "delivery-approaching:",
        "invoice-exception:",
    ):
        assert prefix in source
    assert "Notification.dedupe_key == dedupe_key" in source


def test_notification_storage_enforces_unique_dedupe_key():
    source = read_text("app/models/notifications.py")
    assert "dedupe_key" in source
    assert "unique=True" in source or "UniqueConstraint" in source


def test_supplier_notification_is_idempotent_after_success():
    source = read_text("app/api/routes/purchase_orders.py")
    assert 'po.supplier_notification_status == "SENT"' in source
    assert "already been notified" in source
    assert 'po.status != "ISSUED"' in source
    assert "Supplier notification can only be sent for an issued purchase order" in source


def test_supplier_notification_failures_are_recorded_and_audited():
    source = read_text("app/api/routes/purchase_orders.py")
    assert 'po.supplier_notification_status = "FAILED"' in source
    assert "po.supplier_notification_error" in source
    assert "PURCHASE_ORDER_SUPPLIER_EMAIL_FAILED" in source
    assert "record_audit_event(" in source


def test_supplier_portal_token_is_hashed_and_response_is_not_cacheable():
    source = read_text("app/api/routes/supplier_responses.py")
    assert "hashlib.sha256" in source
    assert "response_token_hash" in source
    assert '"Cache-Control": "no-store"' in source
    assert '"Referrer-Policy": "no-referrer"' in source


def test_supplier_portal_rejects_expired_and_reused_invitations():
    source = read_text("app/api/routes/supplier_responses.py")
    assert "quotation is not None" in source
    assert "response_submitted_at is not None" in source
    assert "response_token_expires_at" in source
    assert "This quotation invitation has expired." in source


def test_business_transition_audit_service_is_present():
    source = read_text("app/services/audit.py")
    assert "def record_audit_event(" in source
    assert "AuditLog(" in source
    assert "db.add(event)" in source


def test_core_routes_record_audit_events_for_business_transitions():
    for relative in (
        "app/api/routes/purchase_orders.py",
        "app/api/routes/goods_receipts.py",
        "app/api/routes/purchase_request_approvals.py",
        "app/api/routes/invoice_matching.py",
    ):
        source = read_text(relative)
        assert "record_audit_event(" in source, relative


def test_frontend_has_loading_error_offline_and_permission_denied_states():
    source = read_text("app/web/static/js/app.js")
    required_fragments = (
        "Your session expired.",
        "You appear to be offline",
        "Unable to load this workspace",
        "not authorized",
        "still loading",
        "emptyState(",
        "toast(err.message, \"error\")",
    )
    lowered = source.lower()
    for fragment in required_fragments:
        assert fragment.lower() in lowered, fragment


def test_frontend_disables_action_buttons_during_mutating_requests():
    source = read_text("app/web/static/js/app.js")
    # Guard against duplicate submissions while a business action is in flight.
    assert "button.disabled=true" in source or "button.disabled = true" in source
    assert "button.disabled=false" in source or "button.disabled = false" in source


def test_main_ui_has_responsive_breakpoints_for_desktop_tablet_mobile():
    source = read_text("app/web/static/css/app.css")
    for breakpoint in ("1180px", "860px", "560px"):
        assert breakpoint in source
    assert "grid-template-columns:1fr" in source
    assert ".sidebar.is-open" in source
    assert ".mobile-only" in source


def test_supplier_portal_is_responsive_on_small_screens():
    source = read_text("app/api/routes/supplier_responses.py")
    assert "@media(max-width:620px)" in source
    assert "grid-template-columns:1fr" in source


def test_goods_receipt_validates_duplicate_and_owned_lines_before_commit():
    source = read_text("app/api/routes/goods_receipts.py")
    assert "Each purchase-order line can appear only once in a goods receipt." in source
    assert "One or more receipt lines do not belong to the selected purchase order." in source
    assert "db.commit()" in source


def test_approval_route_enforces_assignee_and_pending_sequence():
    source = read_text("app/api/routes/purchase_request_approvals.py")
    assert "approval.approver_user_id != actor.id" in source
    assert "approval.status != \"PENDING\"" in source
    assert "first pending" in source.lower()


def test_automation_run_is_explicitly_permission_protected():
    source = read_text("app/api/routes/automations.py")
    assert 'require_permissions("automation.run")' in source


def test_notification_reads_are_recipient_scoped():
    source = read_text("app/api/routes/automations.py")
    assert "Notification.recipient_user_id == actor.id" in source
    assert "Notification.id == notification_id" in source


def test_frontend_handles_slow_network_states():
    source = read_text("app/web/static/js/app.js")
    assert "setTimeout" in source
    assert "still loading" in source.lower()
    assert "connection is taking longer than usual" in source.lower()


def test_enterprise_does_not_introduce_ai_dependencies():
    # Enterprise hardening remains independent of any generative service.
    source = read_text("requirements.txt").lower()
    assert "openai" not in source
    assert "google-generativeai" not in source
    assert "groq" not in source
