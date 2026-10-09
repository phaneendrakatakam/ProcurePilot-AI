import uuid

from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CurrentUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    department_id: uuid.UUID | None
    roles: list[str]
    permissions: list[str]


class AdminUserSummary(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    department_id: uuid.UUID | None
    roles: list[str]
