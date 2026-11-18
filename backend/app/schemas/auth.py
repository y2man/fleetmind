import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.rbac import permissions_for


def _strong(pw: str) -> str:
    if len(pw) < 10 or not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        raise ValueError("Password must be at least 10 characters and include a letter and a number")
    return pw


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)
    full_name: str = Field(min_length=1, max_length=160)
    organization_name: str = Field(min_length=1, max_length=160)
    _pw = field_validator("password")(_strong)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class TokenIn(BaseModel):
    token: str


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    new_password: str = Field(max_length=128)
    _pw = field_validator("new_password")(_strong)


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=40)


class OrgUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    country: str | None = Field(default=None, max_length=80)
    timezone: str | None = Field(default=None, max_length=64)
    fleet_size: int | None = Field(default=None, ge=0, le=100000)


class InviteIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=160)
    role: str


class MemberUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None


class OrgOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    country: str | None
    timezone: str | None
    fleet_size: int | None


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    role: str
    email_verified: bool
    organization: OrgOut
    permissions: list[str]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    dev_link: str | None = None  # development only: emails are not sent, so the link is returned


class MessageOut(BaseModel):
    message: str
    dev_link: str | None = None


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    full_name: str
    role_name: str
    is_active: bool
    email_verified: bool
    last_login_at: datetime | None


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    action: str
    user_id: uuid.UUID | None
    entity_type: str | None
    entity_id: str | None
    ip: str | None
    created_at: datetime


def to_user_out(u) -> UserOut:
    return UserOut(
        id=u.id, email=u.email, full_name=u.full_name, phone=u.phone, role=u.role_name,
        email_verified=u.email_verified, organization=OrgOut.model_validate(u.organization),
        permissions=sorted(permissions_for(u.role_name)),
    )
