from app.seed.bootstrap import PERMISSION_SEEDS, ROLE_PERMISSION_CODES


def test_all_enterprise_roles_have_permissions():
    expected_roles = {
        "EMPLOYEE",
        "MANAGER",
        "PROCUREMENT_ANALYST",
        "PROCUREMENT_HEAD",
        "AP_ANALYST",
        "FINANCE_MANAGER",
        "GOODS_RECEIVER",
        "ADMINISTRATOR",
    }
    assert set(ROLE_PERMISSION_CODES) == expected_roles
    assert all(ROLE_PERMISSION_CODES[role] for role in expected_roles)


def test_only_administrator_has_user_admin_permissions():
    assert "users.read" in ROLE_PERMISSION_CODES["ADMINISTRATOR"]
    assert "users.manage" in ROLE_PERMISSION_CODES["ADMINISTRATOR"]

    for role, permissions in ROLE_PERMISSION_CODES.items():
        if role == "ADMINISTRATOR":
            continue
        assert "users.read" not in permissions
        assert "users.manage" not in permissions
        assert "master_data.manage" not in permissions


def test_administrator_receives_complete_permission_catalog():
    all_permissions = {code for code, _, _ in PERMISSION_SEEDS}
    assert ROLE_PERMISSION_CODES["ADMINISTRATOR"] == all_permissions


def test_core_separation_of_duties():
    assert ROLE_PERMISSION_CODES["EMPLOYEE"] == {
        "purchase_requests.create",
        "purchase_requests.read_own",
    }
    assert "approvals.decide" in ROLE_PERMISSION_CODES["MANAGER"]
    assert "sourcing.manage" in ROLE_PERMISSION_CODES["PROCUREMENT_ANALYST"]
    assert "invoices.review" in ROLE_PERMISSION_CODES["AP_ANALYST"]
    assert "finance.review" in ROLE_PERMISSION_CODES["FINANCE_MANAGER"]
    assert "goods_receipts.manage" in ROLE_PERMISSION_CODES["GOODS_RECEIVER"]
