import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.identity import User
from app.services.auth import get_permission_codes, get_user_by_id


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(str(payload["sub"]))
    except (ValueError, KeyError):
        raise credentials_error

    user = get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise credentials_error
    return user


def require_permissions(*required_permissions: str) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        available = set(get_permission_codes(user))
        missing = set(required_permissions) - available
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return dependency


def require_any_permissions(*required_permissions: str) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        available = set(get_permission_codes(user))
        if not available.intersection(required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return dependency
