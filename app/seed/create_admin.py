from getpass import getpass

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.governance import ActorType
from app.models.identity import Department, Role, User, UserRole
from app.services.audit import record_audit_event


def main() -> None:
    email = input("Administrator email: ").strip().lower()
    full_name = input("Administrator full name: ").strip()
    password = getpass("Administrator password (12+ characters): ")
    password_confirm = getpass("Confirm password: ")

    if not email or "@" not in email:
        raise SystemExit("A valid administrator email is required.")

    if not full_name:
        raise SystemExit("Administrator full name is required.")

    if len(password) < 12:
        raise SystemExit(
            "Administrator password must be at least 12 characters."
        )

    if password != password_confirm:
        raise SystemExit("Passwords do not match.")

    with SessionLocal() as db:
        admin_role = db.scalar(
            select(Role).where(Role.code == "ADMINISTRATOR")
        )

        if not admin_role:
            raise SystemExit(
                "ADMINISTRATOR role is missing. "
                "Run the bootstrap seed first."
            )

        department = db.scalar(
            select(Department).where(Department.code == "PROC")
        )

        user = db.scalar(
            select(User).where(func.lower(User.email) == email)
        )

        created = user is None

        if created:
            user = User(
                email=email,
                full_name=full_name,
                password_hash=hash_password(password),
                department_id=department.id if department else None,
                is_active=True,
            )
            db.add(user)
            db.flush()

        else:
            user.full_name = full_name
            user.password_hash = hash_password(password)
            user.is_active = True

            if user.department_id is None and department:
                user.department_id = department.id

        assignment = db.scalar(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == admin_role.id,
            )
        )

        if not assignment:
            db.add(
                UserRole(
                    user_id=user.id,
                    role_id=admin_role.id,
                )
            )

        record_audit_event(
            db,
            actor_type=ActorType.SYSTEM,
            action=(
                "ADMIN_USER_CREATED"
                if created
                else "ADMIN_USER_BOOTSTRAP_UPDATED"
            ),
            entity_type="user",
            entity_id=str(user.id),
            details={
                "bootstrap": True,
                "existing_user": not created,
            },
        )

        db.commit()

    print(f"Administrator ready: {email}")


if __name__ == "__main__":
    main()