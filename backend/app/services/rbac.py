from sqlalchemy.orm import Session

from app.core.rbac import PERMISSIONS, ROLE_PERMISSIONS
from app.models import Permission, Role, role_permissions


def ensure_roles(db: Session) -> None:
    """Idempotent: mirrors core.rbac into the roles/permissions tables."""
    have_p = {p.code for p in db.query(Permission).all()}
    for code in PERMISSIONS:
        if code not in have_p:
            db.add(Permission(code=code))
    have_r = {r.name for r in db.query(Role).all()}
    for name in ROLE_PERMISSIONS:
        if name not in have_r:
            db.add(Role(name=name))
    db.flush()
    existing = {(r.role_name, r.permission_code) for r in db.execute(role_permissions.select())}
    for role, perms in ROLE_PERMISSIONS.items():
        for code in perms:
            if (role, code) not in existing:
                db.execute(role_permissions.insert().values(role_name=role, permission_code=code))
    db.commit()
