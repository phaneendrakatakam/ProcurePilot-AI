from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.identity import (
    Budget,
    Department,
    Permission,
    Role,
    RolePermission,
    Vendor,
)


ROLE_SEEDS = [
    ("EMPLOYEE", "Employee", "Raise and track purchase requests."),
    ("MANAGER", "Manager", "Approve or reject department purchases."),
    ("PROCUREMENT_ANALYST", "Procurement Analyst", "Manage sourcing exceptions and vendor/quotation issues."),
    ("PROCUREMENT_HEAD", "Procurement Head", "Approve high-value procurement and strategic exceptions."),
    ("AP_ANALYST", "AP Analyst", "Review invoice exceptions and payment-readiness issues."),
    ("FINANCE_MANAGER", "Finance Manager", "Handle finance approvals, budget exceptions, and high-risk cases."),
    ("GOODS_RECEIVER", "Goods Receiver", "Record deliveries and goods receipt notes."),
    ("ADMINISTRATOR", "Administrator", "Manage users, roles, policies, vendors, and system configuration."),
]

PERMISSION_SEEDS = [
    ("purchase_requests.create", "Create purchase requests", "Create employee purchase requests."),
    ("purchase_requests.read_own", "Read own purchase requests", "View purchase requests owned by the user."),
    ("purchase_requests.read_department", "Read department purchase requests", "View department purchase requests."),
    ("purchase_requests.read_all", "Read all purchase requests", "View purchase requests across the enterprise."),
    ("approvals.decide", "Decide approvals", "Approve, reject, or request information."),
    ("sourcing.manage", "Manage sourcing", "Manage RFQs, quotations, and sourcing exceptions."),
    ("goods_receipts.manage", "Manage goods receipts", "Record and update goods receipts."),
    ("invoices.review", "Review invoices", "Review invoice exceptions and extraction issues."),
    ("finance.review", "Finance review", "Handle finance approvals and financial exceptions."),
    ("master_data.manage", "Manage master data", "Manage departments, budgets, vendors, and policy configuration."),
    ("users.read", "Read users", "View user and role assignments."),
    ("users.manage", "Manage users", "Create, activate, deactivate, and assign user roles."),
    ("automation.run", "Run procurement notifications", "Run the notification automation cycle."),
]

ROLE_PERMISSION_CODES = {
    "EMPLOYEE": {"purchase_requests.create", "purchase_requests.read_own"},
    "MANAGER": {"purchase_requests.read_department", "approvals.decide"},
    "PROCUREMENT_ANALYST": {"purchase_requests.read_all", "sourcing.manage"},
    "PROCUREMENT_HEAD": {"purchase_requests.read_all", "sourcing.manage", "approvals.decide"},
    "AP_ANALYST": {"invoices.review"},
    "FINANCE_MANAGER": {"finance.review", "approvals.decide"},
    "GOODS_RECEIVER": {"goods_receipts.manage"},
    "ADMINISTRATOR": {code for code, _, _ in PERMISSION_SEEDS},
}

DEPARTMENT_SEEDS = [
    ("ENG", "Engineering"),
    ("FIN", "Finance"),
    ("OPS", "Operations"),
    ("PROC", "Procurement"),
    ("SALES", "Sales"),
]

VENDOR_SEEDS = [
    ("VEND-001", "Aster Office Solutions Pvt Ltd", "quotes@aster-office.example", 30, Decimal("88.00")),
    ("VEND-002", "BluePeak Technologies Pvt Ltd", "sales@bluepeak-tech.example", 45, Decimal("92.50")),
    ("VEND-003", "Cedar Industrial Supplies Pvt Ltd", "rfq@cedar-industrial.example", 30, Decimal("81.75")),
]


def main() -> None:
    with SessionLocal() as db:
        roles: dict[str, Role] = {}
        for code, name, description in ROLE_SEEDS:
            role = db.scalar(select(Role).where(Role.code == code))
            if not role:
                role = Role(code=code, name=name, description=description)
                db.add(role)
                db.flush()
            roles[code] = role

        permissions: dict[str, Permission] = {}
        for code, name, description in PERMISSION_SEEDS:
            permission = db.scalar(select(Permission).where(Permission.code == code))
            if not permission:
                permission = Permission(code=code, name=name, description=description)
                db.add(permission)
                db.flush()
            permissions[code] = permission

        for role_code, permission_codes in ROLE_PERMISSION_CODES.items():
            role = roles[role_code]
            for permission_code in permission_codes:
                permission = permissions[permission_code]
                existing = db.scalar(
                    select(RolePermission).where(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == permission.id,
                    )
                )
                if not existing:
                    db.add(RolePermission(role_id=role.id, permission_id=permission.id))

        departments: dict[str, Department] = {}
        for code, name in DEPARTMENT_SEEDS:
            department = db.scalar(select(Department).where(Department.code == code))
            if not department:
                department = Department(code=code, name=name)
                db.add(department)
                db.flush()
            departments[code] = department

        for code, legal_name, email, terms, score in VENDOR_SEEDS:
            existing = db.scalar(select(Vendor).where(Vendor.vendor_code == code))
            if not existing:
                db.add(
                    Vendor(
                        vendor_code=code,
                        legal_name=legal_name,
                        email=email,
                        payment_terms_days=terms,
                        reliability_score=score,
                    )
                )

        current_budget = db.scalar(
            select(Budget).where(
                Budget.department_id == departments["ENG"].id,
                Budget.fiscal_year == 2026,
            )
        )
        if not current_budget:
            db.add(
                Budget(
                    department_id=departments["ENG"].id,
                    fiscal_year=2026,
                    currency="INR",
                    allocated_amount=Decimal("2500000.00"),
                    consumed_amount=Decimal("0.00"),
                )
            )

        db.commit()

    print("ProcurePilot fictional enterprise seed data is ready.")


if __name__ == "__main__":
    main()
