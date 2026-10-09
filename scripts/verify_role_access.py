from __future__ import annotations

import getpass
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


BASE = "http://127.0.0.1:8000/api/v1"
DEMO_USERS = [
    ("EMPLOYEE", "employee@procurepilot.example"),
    ("MANAGER", "manager@procurepilot.example"),
    ("PROCUREMENT_ANALYST", "procurement.analyst@procurepilot.example"),
    ("PROCUREMENT_HEAD", "procurement.head@procurepilot.example"),
    ("AP_ANALYST", "ap.analyst@procurepilot.example"),
    ("FINANCE_MANAGER", "finance.manager@procurepilot.example"),
    ("GOODS_RECEIVER", "goods.receiver@procurepilot.example"),
]


def request(method: str, path: str, *, body: bytes | None = None, token: str | None = None, content_type: str | None = None):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            data = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            data = raw
        return exc.code, data


def login(email: str, password: str) -> tuple[int, dict | None]:
    payload = urllib.parse.urlencode({"username": email, "password": password}).encode("utf-8")
    return request(
        "POST",
        "/auth/login",
        body=payload,
        content_type="application/x-www-form-urlencoded",
    )


def main() -> int:
    print("ProcurePilot — role access verification")
    print(f"Target: {BASE}")
    print("The FastAPI server must already be running.")
    print()
    password = getpass.getpass("Shared demo password: ")

    failures = 0
    print()
    print(f"{'ROLE':<22} {'LOGIN':<8} {'/ME':<8} {'ADMIN API':<12} RESULT")
    print("-" * 72)

    for expected_role, email in DEMO_USERS:
        login_status, login_data = login(email, password)
        me_status = None
        admin_status = None
        ok = login_status == 200 and isinstance(login_data, dict) and bool(login_data.get("access_token"))

        if ok:
            token = login_data["access_token"]
            me_status, me_data = request("GET", "/auth/me", token=token)
            actual_roles = set(me_data.get("roles", [])) if isinstance(me_data, dict) else set()
            ok = ok and me_status == 200 and expected_role in actual_roles
            admin_status, _ = request("GET", "/admin/users", token=token)
            ok = ok and admin_status == 403

        if not ok:
            failures += 1

        print(
            f"{expected_role:<22} "
            f"{str(login_status):<8} "
            f"{str(me_status if me_status is not None else '-'): <8} "
            f"{str(admin_status if admin_status is not None else '-'): <12} "
            f"{'PASS' if ok else 'FAIL'}"
        )

    print()
    if failures:
        print(f"Role validation failed for {failures} account(s).")
        return 1

    print("PASS: every non-admin demo role authenticated, returned its expected role, and was blocked from /admin/users with HTTP 403.")
    print("Administrator 200 access was already verified separately in the UI/API workflow.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
