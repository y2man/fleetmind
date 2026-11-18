import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, User


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def get(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def list_by_org(db: Session, org_id: uuid.UUID) -> list[User]:
    return list(db.scalars(select(User).where(User.organization_id == org_id).order_by(User.created_at)))


def get_in_org(db: Session, org_id: uuid.UUID, user_id: uuid.UUID) -> User | None:
    return db.scalar(select(User).where(User.id == user_id, User.organization_id == org_id))


def audit_page(db: Session, org_id: uuid.UUID, limit: int, offset: int) -> list[AuditLog]:
    q = select(AuditLog).where(AuditLog.organization_id == org_id).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(q))
