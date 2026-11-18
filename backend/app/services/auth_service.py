import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from kombu.exceptions import OperationalError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rbac import ASSIGNABLE_ROLES
from app.core.security import (DUMMY_HASH, create_token, decode_token, fingerprint, hash_password, verify_password)
from app.models import Organization, User
from app.repositories import user_repo
from app.schemas.auth import InviteIn, RegisterIn
from app.services import audit, rbac
from app.services.email import send_email

logger = logging.getLogger("fleetmind.auth")


def _link(path: str, token: str) -> str:
    return f"{get_settings().frontend_url}{path}?token={token}"


def _dev(link: str, sent: bool) -> str | None:
    return link if get_settings().is_dev and not sent else None


def _send_email(to: str, subject: str, body: str) -> bool:
    if get_settings().email_delivery_backend != "celery":
        return send_email(to, subject, body)
    from app.tasks.email import deliver_email

    try:
        deliver_email.delay(to, subject, body)
    except OperationalError as exc:
        logger.error("Email queue unavailable error_type=%s", type(exc).__name__)
        return False
    return True


def access_token(user: User) -> str:
    return create_token(str(user.id), "access", timedelta(minutes=get_settings().access_token_minutes), org=str(user.organization_id))


def refresh_token(user: User) -> str:
    return create_token(str(user.id), "refresh", timedelta(days=get_settings().refresh_token_days), org=str(user.organization_id))


def send_verification(user: User) -> str | None:
    token = create_token(str(user.id), "verify", timedelta(hours=48), email=user.email)
    link = _link("/verify-email", token)
    sent = _send_email(user.email, "Verify your FleetMind email", f"Open this link to verify your email:\n{link}")
    return _dev(link, sent)


def _reset_token(user: User, hours: int) -> str:
    return create_token(str(user.id), "reset", timedelta(hours=hours), fp=fingerprint(user.password_hash))


def register(db: Session, data: RegisterIn, ip: str | None) -> tuple[User, str | None]:
    email = data.email.lower()
    if user_repo.get_by_email(db, email):
        raise HTTPException(409, "An account with this email already exists")
    rbac.ensure_roles(db)
    try:
        org = Organization(name=data.organization_name.strip())
        db.add(org)
        db.flush()
        user = User(organization_id=org.id, email=email, password_hash=hash_password(data.password), full_name=data.full_name.strip(), role_name="owner")
        db.add(user)
        db.flush()
        audit.record(db, "auth.register", user=user, ip=ip, entity_type="organization", entity_id=str(org.id))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An account with this email already exists")
    return user, send_verification(user)


def login(db: Session, email: str, password: str, ip: str | None) -> User:
    user = user_repo.get_by_email(db, email)
    ok = verify_password(password, user.password_hash if user else DUMMY_HASH)
    if not (user and ok and user.is_active):
        audit.record(db, "auth.login_failed", user=user if user else None, ip=ip, detail={"email": email.lower()}, commit=True)
        raise HTTPException(401, "Invalid email or password")
    user.last_login_at = datetime.now(timezone.utc)
    audit.record(db, "auth.login", user=user, ip=ip)
    db.commit()
    return user


def user_from_refresh(db: Session, token: str) -> User:
    try:
        payload = decode_token(token, "refresh")
        user = user_repo.get(db, uuid.UUID(payload["sub"]))
    except (ValueError, KeyError):
        raise HTTPException(401, "Session expired")
    if not user or not user.is_active or str(user.organization_id) != payload.get("org"):
        raise HTTPException(401, "Session expired")
    return user


def verify_email(db: Session, token: str) -> None:
    try:
        p = decode_token(token, "verify")
        user = user_repo.get(db, uuid.UUID(p["sub"]))
    except (ValueError, KeyError):
        raise HTTPException(400, "This verification link is invalid or expired")
    if not user or user.email != p.get("email"):
        raise HTTPException(400, "This verification link is invalid or expired")
    user.email_verified = True
    audit.record(db, "auth.email_verified", user=user)
    db.commit()


def forgot_password(db: Session, email: str, ip: str | None) -> str | None:
    user = user_repo.get_by_email(db, email)
    if not (user and user.is_active):
        return None  # same response either way: no account enumeration
    link = _link("/reset-password", _reset_token(user, 1))
    sent = _send_email(user.email, "Reset your FleetMind password", f"Open this link to choose a new password (valid 1 hour):\n{link}")
    audit.record(db, "auth.password_reset_requested", user=user, ip=ip, commit=True)
    return _dev(link, sent)


def reset_password(db: Session, token: str, new_password: str, ip: str | None) -> None:
    try:
        p = decode_token(token, "reset")
        user = user_repo.get(db, uuid.UUID(p["sub"]))
    except (ValueError, KeyError):
        raise HTTPException(400, "This reset link is invalid or expired")
    if not user or p.get("fp") != fingerprint(user.password_hash):
        raise HTTPException(400, "This reset link is invalid or expired")  # also covers already-used links
    user.password_hash = hash_password(new_password)
    audit.record(db, "auth.password_reset", user=user, ip=ip)
    db.commit()


def invite(db: Session, actor: User, data: InviteIn, ip: str | None) -> tuple[User, str | None]:
    if data.role not in ASSIGNABLE_ROLES:
        raise HTTPException(422, "Invalid role")
    if data.role == "admin" and actor.role_name != "owner":
        raise HTTPException(403, "Only the owner can invite admins")
    if user_repo.get_by_email(db, data.email):
        raise HTTPException(409, "An account with this email already exists")
    user = User(organization_id=actor.organization_id, email=data.email.lower(), password_hash=hash_password(secrets.token_urlsafe(24)),
                full_name=data.full_name.strip(), role_name=data.role)
    db.add(user)
    db.flush()
    link = _link("/reset-password", _reset_token(user, 72))
    sent = _send_email(user.email, "You're invited to FleetMind", f"{actor.full_name} invited you. Set your password:\n{link}")
    audit.record(db, "user.invited", user=actor, ip=ip, entity_type="user", entity_id=str(user.id), detail={"role": data.role})
    db.commit()
    return user, _dev(link, sent)
