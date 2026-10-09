"""enterprise enterprise security hardening tests.

These tests intentionally exercise authentication/authorization helpers without
requiring a live database. Route-level assertions verify that sensitive API
surfaces remain protected by the intended permission dependencies.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.api.dependencies.auth as auth
from app.core.security import create_access_token, decode_access_token


ROOT = Path(__file__).resolve().parents[1]


def test_tampered_access_token_is_rejected():
    token = create_access_token(
        subject="12345678-1234-5678-1234-567812345678",
        roles=["EMPLOYEE"],
        permissions=["purchase_requests.create"],
        expires_minutes=5,
    )
    header, payload, signature = token.split(".")
    tampered = f"{header}.{payload}.tampered-{signature}"

    with pytest.raises(ValueError):
        decode_access_token(tampered)


def test_expired_access_token_is_rejected():
    token = create_access_token(
        subject="12345678-1234-5678-1234-567812345678",
        roles=["EMPLOYEE"],
        permissions=[],
        expires_minutes=-1,
    )

    with pytest.raises(ValueError):
        decode_access_token(token)


def test_access_token_with_wrong_type_is_rejected():
    import jwt
    from app.core.config import settings

    token = jwt.encode(
        {
            "sub": "12345678-1234-5678-1234-567812345678",
            "type": "refresh",
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(ValueError, match="Invalid access token payload"):
        decode_access_token(token)


def test_invalid_subject_is_rejected(monkeypatch):
    monkeypatch.setattr(
        auth,
        "decode_access_token",
        lambda _token: {"sub": "not-a-uuid", "type": "access"},
    )

    with pytest.raises(HTTPException) as exc:
        auth.get_current_user("not-used", object())

    assert exc.value.status_code == 401


def test_nonexistent_user_is_rejected(monkeypatch):
    monkeypatch.setattr(
        auth,
        "decode_access_token",
        lambda _token: {"sub": "12345678-1234-5678-1234-567812345678", "type": "access"},
    )
    monkeypatch.setattr(auth, "get_user_by_id", lambda _db, _user_id: None)

    with pytest.raises(HTTPException) as exc:
        auth.get_current_user("not-used", object())

    assert exc.value.status_code == 401


def test_inactive_user_is_rejected(monkeypatch):
    monkeypatch.setattr(
        auth,
        "decode_access_token",
        lambda _token: {"sub": "12345678-1234-5678-1234-567812345678", "type": "access"},
    )
    inactive_user = SimpleNamespace(is_active=False)
    monkeypatch.setattr(auth, "get_user_by_id", lambda _db, _user_id: inactive_user)

    with pytest.raises(HTTPException) as exc:
        auth.get_current_user("not-used", object())

    assert exc.value.status_code == 401


def test_current_user_comes_from_database_not_token_permissions(monkeypatch):
    user = SimpleNamespace(is_active=True, id="db-user")
    monkeypatch.setattr(
        auth,
        "decode_access_token",
        lambda _token: {
            "sub": "12345678-1234-5678-1234-567812345678",
            "type": "access",
            "permissions": ["users.manage"],
        },
    )
    monkeypatch.setattr(auth, "get_user_by_id", lambda _db, _user_id: user)

    result = auth.get_current_user("not-used", object())
    assert result is user


def test_require_permissions_rejects_missing_permission(monkeypatch):
    user = SimpleNamespace()
    monkeypatch.setattr(auth, "get_permission_codes", lambda _user: ["purchase_requests.read_own"])
    dependency = auth.require_permissions("sourcing.manage")

    with pytest.raises(HTTPException) as exc:
        dependency(user)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Insufficient permissions"


def test_require_permissions_accepts_required_permission(monkeypatch):
    user = SimpleNamespace()
    monkeypatch.setattr(auth, "get_permission_codes", lambda _user: ["sourcing.manage"])
    dependency = auth.require_permissions("sourcing.manage")

    assert dependency(user) is user


def test_require_permissions_requires_all_permissions(monkeypatch):
    user = SimpleNamespace()
    monkeypatch.setattr(auth, "get_permission_codes", lambda _user: ["sourcing.manage"])
    dependency = auth.require_permissions("sourcing.manage", "approvals.decide")

    with pytest.raises(HTTPException) as exc:
        dependency(user)

    assert exc.value.status_code == 403


def test_require_any_permissions_accepts_one_matching_permission(monkeypatch):
    user = SimpleNamespace()
    monkeypatch.setattr(auth, "get_permission_codes", lambda _user: ["sourcing.manage"])
    dependency = auth.require_any_permissions("goods_receipts.manage", "sourcing.manage")

    assert dependency(user) is user


def test_require_any_permissions_rejects_when_none_match(monkeypatch):
    user = SimpleNamespace()
    monkeypatch.setattr(auth, "get_permission_codes", lambda _user: ["purchase_requests.read_own"])
    dependency = auth.require_any_permissions("goods_receipts.manage", "sourcing.manage")

    with pytest.raises(HTTPException) as exc:
        dependency(user)

    assert exc.value.status_code == 403


def test_sensitive_routes_have_permission_guards():
    expectations = {
        "app/api/routes/purchase_orders.py": [
            'require_permissions("sourcing.manage")',
        ],
        "app/api/routes/goods_receipts.py": [
            'require_permissions("goods_receipts.manage")',
            'require_any_permissions("goods_receipts.manage", "sourcing.manage")',
        ],
        "app/api/routes/purchase_request_approvals.py": [
            'require_permissions("approvals.decide")',
        ],
        "app/api/routes/invoices.py": [
            'require_permissions("invoices.review")',
        ],
        "app/api/routes/invoice_matching.py": [
            'require_permissions("invoices.review")',
        ],
        "app/api/routes/automations.py": [
            'require_permissions("automation.run")',
        ],
    }

    for relative_path, required_fragments in expectations.items():
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        for fragment in required_fragments:
            assert fragment in source, f"Missing authorization guard: {relative_path}: {fragment}"


def test_po_issue_has_role_boundary_for_procurement_head():
    source = (ROOT / "app/api/routes/purchase_orders.py").read_text(encoding="utf-8")
    assert '"PROCUREMENT_HEAD" not in actor_roles' in source
    assert "Only a Procurement Head can issue a purchase order" in source


def test_approval_detail_and_decision_are_assignee_scoped():
    source = (ROOT / "app/api/routes/purchase_request_approvals.py").read_text(encoding="utf-8")
    assert "approval.approver_user_id != actor.id" in source
    assert "approval.approver_user_id != actor.id" in source


def test_notification_center_is_recipient_scoped_and_read_is_owner_scoped():
    source = (ROOT / "app/api/routes/automations.py").read_text(encoding="utf-8")
    assert "Notification.recipient_user_id == actor.id" in source
    assert "Notification.id == notification_id" in source
    assert "Notification.recipient_user_id == actor.id" in source
