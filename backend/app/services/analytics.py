"""Date-range analytics for the Analytics page, CSV and PDF exports.

Everything here is plain arithmetic over the organization's own records (no language model).
Functions take plain objects, not a database session, so they are easy to test; the API layer
loads the data with `insights.load`.

Conventions
  * A range is whole calendar days in UTC, both ends included. FleetMind does not yet store a
    per-organization time zone, so days near midnight can fall on the neighbouring day locally.
  * The comparison period is the same number of days directly before the range.
  * A delivery counts as late when its deadline falls in the range and it is marked delayed,
    is still open past its deadline, or was delivered after its deadline.
  * Fuel and maintenance amounts have no currency in FleetMind; they are shown as entered.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from app.services.insights import OPEN_DELIVERY, OrgData, aware

MAX_RANGE_DAYS = 366
TOP_N = 10


def bucket_days(span: int) -> int:
    """Days per chart point: daily up to a month, weekly up to six months, then 30-day buckets."""
    return 1 if span <= 31 else 7 if span <= 180 else 30


def day_start(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=timezone.utc)


def _pct_change(cur: float, prev: float) -> float | None:
    return round((cur / prev - 1) * 100, 1) if prev else None


def _is_late(d, now: datetime) -> bool:
    deadline = aware(d.deadline)
    if deadline is None:
        return d.status == "delayed"
    if d.status == "delayed":
        return True
    if d.status in OPEN_DELIVERY:
        return deadline < now
    if d.status == "delivered" and d.delivered_at is not None:
        return aware(d.delivered_at) > deadline
    return False


def _in(dt: datetime | None, a: datetime, b: datetime) -> bool:
    dt = aware(dt)
    return dt is not None and a <= dt < b


def _period(data: OrgData, a: datetime, b: datetime, now: datetime) -> dict:
    created = [d for d in data.deliveries if _in(d.created_at, a, b)]
    delivered = [d for d in data.deliveries if d.status == "delivered" and _in(d.delivered_at, a, b)]
    judged = [d for d in delivered if d.deadline is not None]
    on_time = sum(1 for d in judged if aware(d.delivered_at) <= aware(d.deadline))
    late = [d for d in data.deliveries if d.deadline is not None and _in(d.deadline, a, b) and _is_late(d, now)]
    fuel = [f for f in data.fuel if _in(f.occurred_at, a, b)]
    liters = sum(f.liters for f in fuel)
    cost = sum(float(f.cost) for f in fuel)
    done = [m for m in data.maintenance if m.status == "completed" and _in(m.completed_at, a, b)]
    return {
        "created": len(created), "delivered": len(delivered), "judged": len(judged), "on_time": on_time, "late": len(late),
        "on_time_rate": round(on_time / len(judged) * 100, 1) if judged else None,
        "fuel_cost": round(cost, 2), "liters": round(liters, 1), "fills": len(fuel),
        "cost_per_liter": round(cost / liters, 3) if liters > 0 else None,
        "maint_cost": round(sum(float(m.cost or 0) for m in done), 2), "maint_done": len(done),
    }


def _kpi(key: str, label: str, cur, prev, *, suffix: str = "", decimals: int = 0, good: str = "up") -> dict:
    """good: which direction is an improvement ("up", "down" or "neutral"), used only to colour the change."""
    return {
        "key": key, "label": label, "value": cur, "previous": prev, "suffix": suffix, "decimals": decimals, "good": good,
        "change_pct": None if cur is None or prev is None else _pct_change(cur, prev),
    }


def compute(data: OrgData, start: date, end: date, now: datetime) -> dict:
    span = (end - start).days + 1
    a, b = day_start(start), day_start(end + timedelta(days=1))
    pa, pb = a - timedelta(days=span), a
    cur, prev = _period(data, a, b, now), _period(data, pa, pb, now)

    kpis = [
        _kpi("created", "Deliveries created", cur["created"], prev["created"], good="neutral"),
        _kpi("delivered", "Deliveries completed", cur["delivered"], prev["delivered"]),
        _kpi("on_time_rate", "On-time rate", cur["on_time_rate"], prev["on_time_rate"], suffix="%", decimals=1),
        _kpi("late", "Late deliveries", cur["late"], prev["late"], good="down"),
        _kpi("fuel_cost", "Fuel spend", cur["fuel_cost"], prev["fuel_cost"], decimals=2, good="down"),
        _kpi("liters", "Fuel volume (L)", cur["liters"], prev["liters"], decimals=1, good="neutral"),
        _kpi("cost_per_liter", "Cost per litre", cur["cost_per_liter"], prev["cost_per_liter"], decimals=3, good="down"),
        _kpi("maint_cost", "Maintenance spend", cur["maint_cost"], prev["maint_cost"], decimals=2, good="down"),
    ]

    step = bucket_days(span)
    n = -(-span // step)
    labels = [start + timedelta(days=i * step) for i in range(n)]
    series = [{"label": f"{d:%b} {d.day}", "start": d.isoformat(), "created": 0, "delivered": 0, "late": 0, "fuel_cost": 0.0, "liters": 0.0, "maintenance_cost": 0.0} for d in labels]

    def idx(dt: datetime) -> int:
        return min(max(((aware(dt).date() - start).days) // step, 0), n - 1)

    for d in data.deliveries:
        if _in(d.created_at, a, b):
            series[idx(d.created_at)]["created"] += 1
        if d.status == "delivered" and _in(d.delivered_at, a, b):
            series[idx(d.delivered_at)]["delivered"] += 1
        if d.deadline is not None and _in(d.deadline, a, b) and _is_late(d, now):
            series[idx(d.deadline)]["late"] += 1
    for f in data.fuel:
        if _in(f.occurred_at, a, b):
            p = series[idx(f.occurred_at)]
            p["fuel_cost"] += float(f.cost)
            p["liters"] += f.liters
    for m in data.maintenance:
        if m.status == "completed" and _in(m.completed_at, a, b):
            series[idx(m.completed_at)]["maintenance_cost"] += float(m.cost or 0)
    for p in series:
        p["fuel_cost"], p["liters"], p["maintenance_cost"] = round(p["fuel_cost"], 2), round(p["liters"], 1), round(p["maintenance_cost"], 2)

    status_counts: dict[str, int] = defaultdict(int)
    for d in data.deliveries:
        if _in(d.created_at, a, b):
            status_counts[d.status] += 1
    delivery_status = [{"status": s, "count": c} for s, c in sorted(status_counts.items(), key=lambda kv: -kv[1])]

    vmap, dmap = data.vehicle_by_id, data.driver_by_id
    per_vehicle: dict = defaultdict(lambda: {"liters": 0.0, "cost": 0.0, "fills": 0})
    for f in data.fuel:
        if _in(f.occurred_at, a, b):
            p = per_vehicle[f.vehicle_id]
            p["liters"] += f.liters
            p["cost"] += float(f.cost)
            p["fills"] += 1
    fuel_by_vehicle = []
    for vid, p in per_vehicle.items():
        v = vmap.get(vid)
        fuel_by_vehicle.append({
            "vehicle": v.registration if v else "Unknown", "liters": round(p["liters"], 1), "cost": round(p["cost"], 2),
            "fills": p["fills"], "cost_per_liter": round(p["cost"] / p["liters"], 3) if p["liters"] > 0 else None,
        })
    fuel_by_vehicle.sort(key=lambda r: (-r["cost"], r["vehicle"]))

    per_driver: dict = defaultdict(lambda: [0, 0])  # driver_id -> [on_time, judged]
    delivered_by_driver: dict = defaultdict(int)
    for d in data.deliveries:
        if d.status != "delivered" or d.driver_id is None or not _in(d.delivered_at, a, b):
            continue
        delivered_by_driver[d.driver_id] += 1
        if d.deadline is not None:
            per_driver[d.driver_id][1] += 1
            per_driver[d.driver_id][0] += aware(d.delivered_at) <= aware(d.deadline)
    drivers = []
    for did, count in delivered_by_driver.items():
        drv = dmap.get(did)
        on_time, judged = per_driver.get(did, [0, 0])
        drivers.append({
            "driver": drv.full_name if drv else "Unknown", "delivered": count, "judged": judged, "on_time": on_time,
            "late": judged - on_time, "on_time_rate_pct": round(on_time / judged * 100, 1) if judged else None,
        })
    drivers.sort(key=lambda r: (-r["delivered"], r["driver"]))

    kinds: dict = defaultdict(lambda: [0, 0.0])
    for m in data.maintenance:
        if m.status == "completed" and _in(m.completed_at, a, b):
            kinds[m.kind][0] += 1
            kinds[m.kind][1] += float(m.cost or 0)
    maintenance_by_kind = [{"kind": k, "count": c, "cost": round(cost, 2)} for k, (c, cost) in sorted(kinds.items())]

    vehicles_by_status = {s: 0 for s in ("active", "idle", "maintenance", "retired")}
    for v in data.vehicles:
        vehicles_by_status[v.status] = vehicles_by_status.get(v.status, 0) + 1

    notes = [
        "Days are UTC calendar days. Fuel and maintenance amounts have no currency; they are shown as entered.",
        "Late deliveries are counted by deadline date: marked delayed, still open past the deadline, or delivered after it.",
        "Percent changes compare with the previous period of the same length, and are blank when that period has no data.",
    ]
    if not (cur["created"] or cur["delivered"] or cur["fills"] or cur["maint_done"]):
        notes.append("There is no activity in this range. Try a longer range.")
    if cur["delivered"] and cur["judged"] < cur["delivered"]:
        notes.append(f"{cur['delivered'] - cur['judged']} completed deliveries had no deadline and are left out of the on-time rate.")

    return {
        "range": {"start": start.isoformat(), "end": end.isoformat(), "days": span, "bucket_days": step},
        "previous_range": {"start": (start - timedelta(days=span)).isoformat(), "end": (start - timedelta(days=1)).isoformat()},
        "kpis": kpis, "series": series, "delivery_status": delivery_status,
        "fuel_by_vehicle": fuel_by_vehicle[:TOP_N], "drivers": drivers[:TOP_N],
        "maintenance_by_kind": maintenance_by_kind, "vehicles_by_status": vehicles_by_status, "notes": notes,
        "has_data": bool(cur["created"] or cur["delivered"] or cur["fills"] or cur["maint_done"] or cur["late"]),
    }
