import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies.auth import require_permissions
from app.core.database import get_db
from app.core.security import hash_password
from app.models.governance import ActorType
from app.models.identity import Department, Role, User, UserRole
from app.schemas.admin import RoleSummary, UserCreate, UserDetail, UserUpdate
from app.services.audit import record_audit_event
from app.services.auth import get_role_codes

router = APIRouter(prefix="/admin", tags=["admin"])


def _load_user(db: Session, user_id: uuid.UUID) -> User | None:
    return db.scalar(
        select(User)
        .options(selectinload(User.roles).selectinload(UserRole.role))
        .where(User.id == user_id)
    )


def _to_user_detail(user: User) -> UserDetail:
    return UserDetail(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        department_id=user.department_id,
        roles=get_role_codes(user),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _resolve_roles(db: Session, role_codes: list[str]) -> list[Role]:
    normalized = sorted({code.strip().upper() for code in role_codes if code.strip()})
    if not normalized:
        return []
    roles = list(db.scalars(select(Role).where(Role.code.in_(normalized))).all())
    found = {role.code for role in roles}
    missing = set(normalized) - found
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown role code(s): {', '.join(sorted(missing))}",
        )
    return roles


def _validate_department(db: Session, department_id: uuid.UUID | None) -> None:
    if department_id is None:
        return
    if db.get(Department, department_id) is None:
        raise HTTPException(status_code=400, detail="Department not found")


@router.get("/roles", response_model=list[RoleSummary])
def list_roles(
    _: User = Depends(require_permissions("users.read")),
    db: Session = Depends(get_db),
) -> list[Role]:
    return list(db.scalars(select(Role).order_by(Role.code)).all())


@router.get("/users", response_model=list[UserDetail])
def list_users(
    _: User = Depends(require_permissions("users.read")),
    db: Session = Depends(get_db),
) -> list[UserDetail]:
    stmt = (
        select(User)
        .options(selectinload(User.roles).selectinload(UserRole.role))
        .order_by(User.email)
    )
    return [_to_user_detail(user) for user in db.scalars(stmt).all()]


@router.get("/users/{user_id}", response_model=UserDetail)
def get_user(
    user_id: uuid.UUID,
    _: User = Depends(require_permissions("users.read")),
    db: Session = Depends(get_db),
) -> UserDetail:
    user = _load_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _to_user_detail(user)


@router.post("/users", response_model=UserDetail, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    actor: User = Depends(require_permissions("users.manage")),
    db: Session = Depends(get_db),
) -> UserDetail:
    email = str(payload.email).strip().lower()
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        raise HTTPException(status_code=409, detail="A user with that email already exists")

    _validate_department(db, payload.department_id)
    roles = _resolve_roles(db, payload.role_codes)

    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        department_id=payload.department_id,
        is_active=payload.is_active,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A user with that email already exists")
    for role in roles:
        db.add(UserRole(user_id=user.id, role_id=role.id))

    record_audit_event(
        db,
        actor_type=ActorType.HUMAN,
        actor_user_id=actor.id,
        action="USER_CREATED",
        entity_type="user",
        entity_id=str(user.id),
        details={"email": user.email, "roles": sorted(role.code for role in roles)},
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="User could not be created due to a uniqueness conflict")

    return _to_user_detail(_load_user(db, user.id))


@router.patch("/users/{user_id}", response_model=UserDetail)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    actor: User = Depends(require_permissions("users.manage")),
    db: Session = Depends(get_db),
) -> UserDetail:
    user = _load_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    changes: dict[str, object] = {}

    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
        changes["full_name"] = user.full_name

    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
        changes["password_changed"] = True

    if "department_id" in payload.model_fields_set:
        _validate_department(db, payload.department_id)
        user.department_id = payload.department_id
        changes["department_id"] = str(payload.department_id) if payload.department_id else None

    if payload.is_active is not None:
        if user.id == actor.id and payload.is_active is False:
            raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
        user.is_active = payload.is_active
        changes["is_active"] = payload.is_active

    if payload.role_codes is not None:
        roles = _resolve_roles(db, payload.role_codes)
        user.roles.clear()
        db.flush()
        for role in roles:
            user.roles.append(UserRole(role_id=role.id))
        changes["roles"] = sorted(role.code for role in roles)

    record_audit_event(
        db,
        actor_type=ActorType.HUMAN,
        actor_user_id=actor.id,
        action="USER_UPDATED",
        entity_type="user",
        entity_id=str(user.id),
        details=changes,
    )
    db.commit()
    return _to_user_detail(_load_user(db, user.id))
