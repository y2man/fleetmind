"""Dashboard summary computed from real organization data (no demo values)."""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require
from app.core.database import get_db
from app.models import AuditLog, Delivery, Driver, FuelTransaction, MaintenanceRecord, User, Vehicle
from app.schemas.fleet import ActivityItem, Alert, DashboardOut, Kpi, SeriesPoint, UpcomingMaintenance

router = APIRouter(tags=["dashboard"])

BUCKET_DAYS = {7: 1, 30: 3, 90: 10}  # days per chart bucket for each range
OPEN_DELIVERY = {"pending", "assigned", "in_transit"}
EXPIRY_WARN_DAYS = 30
ACTIVITY_ENTITIES = ("vehicle", "driver", "delivery", "fuel_transaction", "maintenance")


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; treat them as UTC so comparisons are safe."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(days: int = Query(30), user: User = Depends(require("analytics:read")), db: Session = Depends(get_db)):
    if days not in BUCKET_DAYS:
        days = 30
    org = user.organization_id
    now = datetime.now(timezone.utc)
    today = now.date()
    start = now - timedelta(days=days)

    vehicles = list(db.scalars(select(Vehicle).where(Vehicle.organization_id == org)))
    drivers = list(db.scalars(select(Driver).where(Driver.organization_id == org)))
    deliveries = list(db.scalars(select(Delivery).where(Delivery.organization_id == org)))
    fuel = [f for f in db.scalars(select(FuelTransaction).where(FuelTransaction.organization_id == org)) if (_aware(f.occurred_at) or now) >= start]
    maint = list(db.scalars(select(MaintenanceRecord).where(MaintenanceRecord.organization_id == org)))

    by_status = {s: 0 for s in ("active", "idle", "maintenance", "retired")}
    for v in vehicles:
        by_status[v.status] = by_status.get(v.status, 0) + 1
    in_service = len(vehicles) - by_status["retired"]

    def is_late(d: Delivery) -> bool:
        dl = _aware(d.deadline)
        return d.status == "delayed" or (d.status in OPEN_DELIVERY and dl is not None and dl < now)

    completed = [d for d in deliveries if d.status == "delivered" and (_aware(d.delivered_at) or now) >= start]
    delayed = [d for d in deliveries if is_late(d) and (_aware(d.deadline) or now) >= start]
    active_deliveries = [d for d in deliveries if d.status in ("assigned", "in_transit")]
    fuel_spend = sum(float(f.cost) for f in fuel)
    done_or_late = len(completed) + len(delayed)

    kpis = [
        Kpi(key="vehicles", label="Total vehicles", value=len(vehicles)),
        Kpi(key="active", label="Active vehicles", value=by_status["active"]),
        Kpi(key="available", label="Available", value=by_status["idle"]),
        Kpi(key="maintenance", label="In maintenance", value=by_status["maintenance"]),
        Kpi(key="active_deliveries", label="Active deliveries", value=len(active_deliveries)),
        Kpi(key="completed", label="Completed deliveries", value=len(completed)),
        Kpi(key="delayed", label="Delayed deliveries", value=len(delayed)),
        Kpi(key="drivers", label="Drivers", value=len(drivers)),
        Kpi(key="fuel", label="Fuel spend", value=round(fuel_spend, 2), decimals=2),
        Kpi(key="utilization", label="Fleet utilization", value=(by_status["active"] / in_service * 100) if in_service else None, suffix="%", decimals=1),
        Kpi(key="success", label="Delivery success", value=(len(completed) / done_or_late * 100) if done_or_late else None, suffix="%", decimals=1),
    ]

    # Chart buckets, oldest first. Each point is labeled with its first day.
    step = BUCKET_DAYS[days]
    n = days // step
    first = today - timedelta(days=days - 1)
    labels = [first + timedelta(days=i * step) for i in range(n)]
    idx = lambda d: min(max((d - first).days // step, 0), n - 1)  # noqa: E731
    del_series = [SeriesPoint(label=f"{d:%b} {d.day}") for d in labels]
    fuel_series = [SeriesPoint(label=f"{d:%b} {d.day}") for d in labels]
    for d in completed:
        del_series[idx((_aware(d.delivered_at) or now).date())].completed += 1
    for d in delayed:
        if d.deadline:
            del_series[idx(_aware(d.deadline).date())].delayed += 1
    for f in fuel:
        fuel_series[idx((_aware(f.occurred_at) or now).date())].cost += float(f.cost)
    for p in fuel_series:
        p.cost = round(p.cost, 2)

    # Alerts: expiring documents, overdue maintenance and late deliveries.
    alerts: list[Alert] = []
    soon = today + timedelta(days=EXPIRY_WARN_DAYS)

    def expiry(kind: str, who: str, when: date | None) -> None:
        if when is None:
            return
        if when < today:
            alerts.append(Alert(severity="critical", text=f"{who}: {kind} expired on {when.isoformat()}"))
        elif when <= soon:
            alerts.append(Alert(severity="warning", text=f"{who}: {kind} expires on {when.isoformat()}"))

    for v in vehicles:
        if v.status != "retired":
            expiry("insurance", v.registration, v.insurance_expiry)
            expiry("registration", v.registration, v.registration_expiry)
    for d in drivers:
        expiry("license", d.full_name, d.license_expiry)
    vlabel = {v.id: v.registration for v in vehicles}
    for m in maint:
        if m.status == "scheduled" and m.scheduled_for and m.scheduled_for < today:
            alerts.append(Alert(severity="critical", text=f"{vlabel.get(m.vehicle_id, 'Vehicle')}: maintenance overdue ({m.description})"))
    for d in deliveries:
        if is_late(d):
            alerts.append(Alert(severity="warning", text=f"Delivery {d.reference} is late or delayed"))
    alerts.sort(key=lambda a: a.severity != "critical")

    upcoming = sorted(
        (m for m in maint if m.status in ("scheduled", "in_progress")),
        key=lambda m: (m.scheduled_for is None, m.scheduled_for or today),
    )[:5]
    maintenance = [UpcomingMaintenance(vehicle=vlabel.get(m.vehicle_id, "Vehicle"), task=m.description, due=m.scheduled_for, overdue=bool(m.scheduled_for and m.scheduled_for < today and m.status == "scheduled")) for m in upcoming]

    logs = list(db.scalars(
        select(AuditLog).where(AuditLog.organization_id == org, AuditLog.entity_type.in_(ACTIVITY_ENTITIES)).order_by(AuditLog.created_at.desc()).limit(8)
    ))
    names = {u.id: u.full_name for u in db.scalars(select(User).where(User.organization_id == org))}
    activity = []
    for lg in logs:
        verb = lg.action.split(".")[-1]
        what = (lg.entity_type or "record").replace("_", " ")
        lab = (lg.detail or {}).get("label")
        activity.append(ActivityItem(text=f"{names.get(lg.user_id, 'Someone')} {verb} {what}{f' {lab}' if lab else ''}", at=_aware(lg.created_at)))

    return DashboardOut(
        days=days, kpis=kpis, deliveries=del_series, fuel=fuel_series, vehicle_status=by_status,
        alerts=alerts[:8], activity=activity, maintenance=maintenance,
        has_data=bool(vehicles or drivers or deliveries or fuel or maint),
    )
