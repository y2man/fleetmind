"""Writes the demo data set to the database. Idempotent and limited to the demo organization.

Safety rules (each one is tested):
  * Running it twice does nothing the second time unless reset=True.
  * Reset only ever deletes the organization named DEMO_ORG_NAME, and only when every user in it
    is one of the demo accounts. A real customer who happens to pick the same name is never touched.
  * It refuses to run in production unless allow_production=True (the demo password is public).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import (AIInsight, AuditLog, Delivery, Driver, FuelTransaction, Geofence, Inspection, MaintenanceRecord,
                        Notification, NotificationRead, Organization, Route, Stop, User, Vehicle, VehicleLocation)
from app.seed.generator import DEMO_ORG_NAME, DEMO_PASSWORD, DEMO_USERS, SeedData, build
from app.services import audit, rbac

DEMO_EMAILS = {u["email"] for u in DEMO_USERS}
DEFAULT_SEED = 20260101


class SeedError(RuntimeError):
    pass


def _find_demo_org(db: Session) -> Organization | None:
    return db.scalar(select(Organization).where(Organization.name == DEMO_ORG_NAME))


def _delete_org(db: Session, org: Organization) -> None:
    """Explicit, dependency-ordered delete (does not rely on database-level cascades)."""
    users = list(db.scalars(select(User).where(User.organization_id == org.id)))
    foreign = [u.email for u in users if u.email not in DEMO_EMAILS]
    if foreign:
        raise SeedError(f"Organization '{org.name}' has non-demo users ({', '.join(foreign)}); refusing to delete it.")
    oid = org.id
    note_ids = select(Notification.id).where(Notification.organization_id == oid)
    db.execute(delete(NotificationRead).where(NotificationRead.notification_id.in_(note_ids)))
    for model in (Notification, Stop, Delivery, Route, FuelTransaction, MaintenanceRecord, Inspection, VehicleLocation,
                  Vehicle, Driver, Geofence, AIInsight, AuditLog, User):
        db.execute(delete(model).where(model.organization_id == oid))
    db.delete(org)
    db.flush()


def _insert(db: Session, org_id, data: SeedData, now: datetime) -> None:
    created = now - timedelta(days=100)

    def add(model, rows: list[dict], **defaults) -> None:
        db.add_all([model(organization_id=org_id, **{**defaults, **r}) for r in rows])
        db.flush()  # keeps foreign-key order explicit: parents are written before children

    add(Driver, data.drivers, created_at=created, updated_at=created)
    add(Vehicle, data.vehicles, created_at=created, updated_at=created)
    add(Route, data.routes)
    add(Delivery, data.deliveries)
    add(Stop, data.stops)
    add(FuelTransaction, data.fuel)
    add(MaintenanceRecord, data.maintenance)
    add(Geofence, data.geofences)


def seed(db: Session, *, reset: bool = False, seed_number: int = DEFAULT_SEED, now: datetime | None = None,
         allow_production: bool = False) -> dict:
    """Create the demo organization, users and records. Returns {"status", "counts", "planted"}."""
    if get_settings().environment == "production" and not allow_production:
        raise SeedError("Refusing to seed demo data in production (the demo password is public). Pass allow_production=True to override.")
    now = now or datetime.now(timezone.utc)
    existing = _find_demo_org(db)
    if existing is not None:
        if not reset:
            return {"status": "exists", "counts": {}, "planted": []}
        _delete_org(db, existing)
    taken = db.scalar(select(User).where(User.email.in_(DEMO_EMAILS)))
    if taken is not None:
        raise SeedError(f"{taken.email} already belongs to another organization; cannot create the demo accounts.")

    rbac.ensure_roles(db)
    org = Organization(name=DEMO_ORG_NAME, country="Ethiopia", timezone="Africa/Addis_Ababa", fleet_size=14)
    db.add(org)
    db.flush()
    owner = None
    for u in DEMO_USERS:
        user = User(organization_id=org.id, email=u["email"], full_name=u["full_name"], role_name=u["role_name"],
                    password_hash=hash_password(DEMO_PASSWORD), email_verified=True)
        db.add(user)
        owner = owner or user
    db.flush()
    data = build(seed_number, now)
    _insert(db, org.id, data, now)
    audit.record(db, "seed.demo_data", user=owner, entity_type="organization", entity_id=str(org.id), detail={"counts": data.counts()})
    db.commit()
    return {"status": "reset" if reset else "created", "counts": data.counts(), "planted": data.planted}
