from getpass import getpass

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.governance import ActorType
from app.models.identity import Department, Role, User, UserRole
from app.services.audit import record_audit_event


DEMO_USERS = [
    {
        "email": "employee@procurepilot.example",
        "full_name": "Aarav Employee",
        "role": "EMPLOYEE",
        "department": "ENG",
    },
    {
        "email": "manager@procurepilot.example",
        "full_name": "Meera Manager",
        "role": "MANAGER",
        "department": "ENG",
    },
    {
        "email": "procurement.analyst@procurepilot.example",
        "full_name": "Rohan Procurement",
        "role": "PROCUREMENT_ANALYST",
        "department": "PROC",
    },
    {
        "email": "procurement.head@procurepilot.example",
        "full_name": "Ananya Procurement Head",
        "role": "PROCUREMENT_HEAD",
        "department": "PROC",
    },
    {
        "email": "ap.analyst@procurepilot.example",
        "full_name": "Kavya AP Analyst",
        "role": "AP_ANALYST",
        "department": "FIN",
    },
    {
        "email": "finance.manager@procurepilot.example",
        "full_name": "Vikram Finance",
        "role": "FINANCE_MANAGER",
        "department": "FIN",
    },
    {
        "email": "goods.receiver@procurepilot.example",
        "full_name": "Nikhil Receiver",
        "role": "GOODS_RECEIVER",
        "department": "OPS",
    },
]


def _load_user(db, email: str) -> User | None:
    return db.scalar(
        select(User)
        .options(selectinload(User.roles).selectinload(UserRole.role))
        .where(func.lower(User.email) == email.lower())
    )


def main() -> None:
    print("ProcurePilot — role-demo user bootstrap")
    print("Creates/refreshes fictional local-development users only.")
    password = getpass("Shared temporary demo password (12+ characters): ")
    confirm = getpass("Confirm temporary password: ")

    if len(password) < 12:
        raise SystemExit("Password must be at least 12 characters.")
    if password != confirm:
        raise SystemExit("Passwords do not match.")

    with SessionLocal() as db:
        roles = {
            role.code: role
            for role in db.scalars(select(Role)).all()
        }
        departments = {
            department.code: department
            for department in db.scalars(select(Department)).all()
        }

        required_roles = {row["role"] for row in DEMO_USERS}
        required_departments = {row["department"] for row in DEMO_USERS}
        missing_roles = sorted(required_roles - roles.keys())
        missing_departments = sorted(required_departments - departments.keys())
        if missing_roles or missing_departments:
            problems = []
            if missing_roles:
                problems.append(f"roles: {', '.join(missing_roles)}")
            if missing_departments:
                problems.append(f"departments: {', '.join(missing_departments)}")
            raise SystemExit(
                "Required seed data is missing (" + "; ".join(problems) + "). "
                "Run: python -m app.seed.bootstrap"
            )

        created = 0
        refreshed = 0

        for row in DEMO_USERS:
            email = row["email"].lower()
            role = roles[row["role"]]
            department = departments[row["department"]]
            user = _load_user(db, email)
            is_new = user is None

            if is_new:
                user = User(
                    email=email,
                    full_name=row["full_name"],
                    password_hash=hash_password(password),
                    department_id=department.id,
                    is_active=True,
                )
                db.add(user)
                db.flush()
                user.roles.append(UserRole(role_id=role.id))
                created += 1
            else:
                user.full_name = row["full_name"]
                user.password_hash = hash_password(password)
                user.department_id = department.id
                user.is_active = True
                user.roles.clear()
                db.flush()
                user.roles.append(UserRole(role_id=role.id))
                refreshed += 1

            record_audit_event(
                db,
                actor_type=ActorType.SYSTEM,
                action="ROLE_DEMO_USER_CREATED" if is_new else "ROLE_DEMO_USER_REFRESHED",
                entity_type="user",
                entity_id=str(user.id),
                details={
                    "email": email,
                    "role": row["role"],
                    "department": row["department"],
                    "development_fixture": True,
                },
            )

        db.commit()

    print()
    print(f"Role-demo users ready. Created: {created}; refreshed: {refreshed}")
    print("Use the shared temporary password you just entered.")
    print()
    for row in DEMO_USERS:
        print(f"{row['role']:<22} {row['email']}")
    print()
    print("Existing Administrator accounts were not modified.")


if __name__ == "__main__":
    main()
