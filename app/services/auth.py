import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.security import verify_password
from app.models.identity import Role, RolePermission, User, UserRole


def _user_load_options():
    return (
        selectinload(User.roles)
        .selectinload(UserRole.role)
        .selectinload(Role.permissions)
        .selectinload(RolePermission.permission)
    )


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized = email.strip().lower()
    stmt = (
        select(User)
        .options(_user_load_options())
        .where(func.lower(User.email) == normalized)
    )
    return db.scalar(stmt)


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    stmt = select(User).options(_user_load_options()).where(User.id == user_id)
    return db.scalar(stmt)


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_role_codes(user: User) -> list[str]:
    return sorted({user_role.role.code for user_role in user.roles})


def get_permission_codes(user: User) -> list[str]:
    return sorted(
        {
            role_permission.permission.code
            for user_role in user.roles
            for role_permission in user_role.role.permissions
        }
    )
