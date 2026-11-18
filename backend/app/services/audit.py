from sqlalchemy.orm import Session

from app.models import AuditLog


def record(db: Session, action: str, *, user=None, org_id=None, entity_type=None, entity_id=None, ip=None, detail=None, commit=False) -> None:
    db.add(AuditLog(
        action=action, user_id=user.id if user else None,
        organization_id=org_id or (user.organization_id if user else None),
        entity_type=entity_type, entity_id=entity_id, ip=ip, detail=detail,
    ))
    if commit:
        db.commit()
