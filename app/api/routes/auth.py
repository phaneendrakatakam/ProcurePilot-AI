from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.models.governance import ActorType
from app.models.identity import User
from app.schemas.auth import CurrentUserResponse, TokenResponse
from app.services.audit import record_audit_event
from app.services.auth import (
    authenticate_user,
    get_permission_codes,
    get_role_codes,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = authenticate_user(db, form.username, form.password)
    if not user:
        record_audit_event(
            db,
            actor_type=ActorType.HUMAN,
            action="AUTH_LOGIN_FAILED",
            entity_type="authentication",
            entity_id="login",
            details={"reason": "invalid_credentials"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    roles = get_role_codes(user)
    permissions = get_permission_codes(user)
    token = create_access_token(
        subject=str(user.id),
        roles=roles,
        permissions=permissions,
    )

    record_audit_event(
        db,
        actor_type=ActorType.HUMAN,
        actor_user_id=user.id,
        action="AUTH_LOGIN_SUCCESS",
        entity_type="user",
        entity_id=str(user.id),
        details={"roles": roles},
    )
    db.commit()

    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=CurrentUserResponse)
def me(user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        department_id=user.department_id,
        roles=get_role_codes(user),
        permissions=get_permission_codes(user),
    )
