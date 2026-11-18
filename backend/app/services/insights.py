"""Deterministic fleet analytics behind the AI center.

Everything here is plain statistics and rules over the organization's own records.
No language model is involved, so results are repeatable and explainable. The AI
assistant calls these functions as tools and the report builder uses them as facts;
the model only explains or summarizes what they return.

The functions take plain objects (no database session) so they are easy to test.
Only `load` touches the database.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from app.services.routing import Assumptions, haversine_km

OPEN_DELIVERY = {"pending", "assigned", "in_transit"}
Z_LIMIT = 3.5  # modified z-score above which a value counts as an outlier
MIN_INTERVALS = 5  # fill-up intervals needed before a vehicle's consumption is screened
MIN_PRICE_GROUP = 8  # fuel purchases of one fuel type needed before prices are compared
MIN_INTERVAL_KM = 20  # shorter intervals say little about consumption (top-ups)
SEVERITY_RANK = {"critical": 0, "warning": 1, "info": 2}
RISK_RANK = {"late": 0, "high": 1, "medium": 2, "low": 3}


def aware(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; treat them as UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _iso(dt: datetime | date | None) -> str | None:
    return dt.isoformat() if dt is not None else None


@dataclass
class OrgData:
    vehicles: list = field(default_factory=list)
    drivers: list = field(default_factory=list)
    deliveries: list = field(default_factory=list)
    fuel: list = field(default_factory=list)
    maintenance: list = field(default_factory=list)

    @property
    def vehicle_by_id(self) -> dict:
        return {v.id: v for v in self.vehicles}

    @property
    def driver_by_id(self) -> dict:
        return {d.id: d for d in self.drivers}


def load(db, org_id) -> OrgData:
    """Read the organization's records. Every query is limited to the organization."""
    from sqlalchemy import select

    from app.models import Delivery, Driver, FuelTransaction, MaintenanceRecord, Vehicle

    def rows(model):
        return list(db.scalars(select(model).where(model.organization_id == org_id)))

    return OrgData(rows(Vehicle), rows(Driver), rows(Delivery), rows(FuelTransaction), rows(MaintenanceRecord))


def _robust(values: list[float]) -> tuple[float, float]:
    """Median and a robust spread (scaled MAD). Falls back to 5% of the median when all values are equal."""
    med = statistics.median(values)
    scale = 1.4826 * statistics.median([abs(v - med) for v in values])
    if scale < 1e-9:
        scale = max(abs(med) * 0.05, 1e-6)
    return med, scale


def _r(x: float | None, digits: int = 2) -> float | None:
    return None if x is None else round(float(x), digits)


# ------------------------------------------------------------ fuel anomalies
ANOMALY_METHODS = [
    "Consumption: litres per 100 km between consecutive fill-ups (needs odometer readings; assumes the tank is filled each time), compared with the same vehicle's own median. Needs at least 5 intervals of 20 km or more.",
    "Fill size: litres in one purchase compared with the vehicle's own median (needs at least 5 purchases).",
    "Price: cost per litre compared with the median for the same fuel type (needs at least 8 purchases).",
    "Data checks: two purchases for one vehicle within an hour, odometer going backwards, and purchases with no distance driven.",
    "Outliers use a robust modified z-score (above 3.5) plus a minimum relative difference, so one odd value does not hide others.",
]
ANOMALY_LIMITATIONS = [
    "These are statistical flags worth checking, not proof of theft, fraud or a fault. Partial fills, a wrong odometer entry or a different route can all look unusual.",
    "Fuel costs have no currency in FleetMind, so prices are compared only with each other.",
]


def fuel_anomalies(data: OrgData, now: datetime, days: int = 90) -> dict:
    since = now - timedelta(days=days)
    vmap = data.vehicle_by_id
    by_vehicle: dict = defaultdict(list)
    for f in data.fuel:
        by_vehicle[f.vehicle_id].append(f)

    items: list[dict] = []
    screened = not_enough = 0
    prices: dict[str, list[tuple]] = defaultdict(list)

    def when(tx) -> datetime:
        return aware(tx.occurred_at) or now

    def add(tx, kind: str, severity: str, title: str, detail: str, evidence: dict) -> None:
        if when(tx) < since:
            return  # older purchases are only used as a baseline
        v = vmap[tx.vehicle_id]
        items.append({
            "id": f"{kind}:{tx.id}", "kind": kind, "severity": severity, "title": title, "detail": detail,
            "vehicle_id": str(v.id), "registration": v.registration, "transaction_id": str(tx.id),
            "occurred_at": when(tx), "evidence": evidence,
        })

    for vid, txs in by_vehicle.items():
        v = vmap.get(vid)
        if v is None:
            continue
        txs.sort(key=when)
        intervals: list[tuple] = []  # (transaction, l_per_100km, km)
        last_odo = None
        prev = None
        for tx in txs:
            if prev is not None and when(tx) - when(prev) <= timedelta(minutes=60):
                add(tx, "possible_duplicate", "warning", "Two fuel purchases within an hour",
                    f"{v.registration} has two purchases {int((when(tx) - when(prev)).total_seconds() // 60)} minutes apart ({tx.liters:.1f} L and {prev.liters:.1f} L). One may be a duplicate entry.",
                    {"minutes_apart": int((when(tx) - when(prev)).total_seconds() // 60), "liters": _r(tx.liters, 1), "previous_liters": _r(prev.liters, 1)})
            prev = tx
            if tx.odometer_km is None:
                continue
            if last_odo is not None:
                dist = tx.odometer_km - last_odo.odometer_km
                if dist < 0:
                    add(tx, "odometer_regression", "warning", "Odometer went backwards",
                        f"{v.registration}: odometer {tx.odometer_km:,} km is lower than the earlier reading {last_odo.odometer_km:,} km. Check for a typing mistake.",
                        {"odometer_km": tx.odometer_km, "previous_odometer_km": last_odo.odometer_km})
                    continue  # keep the earlier reading as the baseline
                if dist == 0 and tx.liters > 0:
                    add(tx, "no_distance", "info", "Fuel bought with no distance driven",
                        f"{v.registration}: {tx.liters:.1f} L bought but the odometer did not change since the last reading.",
                        {"liters": _r(tx.liters, 1), "odometer_km": tx.odometer_km})
                elif dist >= MIN_INTERVAL_KM and tx.liters > 0 and v.fuel_type != "electric":
                    intervals.append((tx, tx.liters / dist * 100, dist))
            last_odo = tx

        if len(intervals) >= MIN_INTERVALS:
            screened += 1
            med, scale = _robust([i[1] for i in intervals])
            for tx, l100, km in intervals:
                z = (l100 - med) / scale
                ev = {"l_per_100km": _r(l100), "typical_l_per_100km": _r(med), "distance_km": _r(km, 0), "liters": _r(tx.liters, 1), "intervals_used": len(intervals), "z_score": _r(z, 1)}
                pct = round((l100 / med - 1) * 100)
                if z > Z_LIMIT and l100 > med * 1.25:
                    add(tx, "high_consumption", "critical" if l100 > med * 1.6 else "warning", f"Fuel use {pct}% above this vehicle's norm",
                        f"{v.registration} used {l100:.1f} L/100 km over {km:.0f} km, against a typical {med:.1f} L/100 km for this vehicle (median of {len(intervals)} intervals).", ev)
                elif z < -Z_LIMIT and l100 < med * 0.6:
                    add(tx, "low_consumption", "info", f"Fuel use {abs(pct)}% below this vehicle's norm",
                        f"{v.registration} used only {l100:.1f} L/100 km over {km:.0f} km (typical {med:.1f}). This often means a missed fill-up entry or a wrong odometer value.", ev)
        elif v.fuel_type != "electric":
            not_enough += 1

        if len(txs) >= MIN_INTERVALS:
            med, scale = _robust([t.liters for t in txs])
            for tx in txs:
                if (tx.liters - med) / scale > Z_LIMIT and tx.liters > med * 1.5:
                    add(tx, "large_fill", "warning", "Unusually large fill",
                        f"{v.registration}: {tx.liters:.1f} L in one purchase, against a typical {med:.1f} L for this vehicle.",
                        {"liters": _r(tx.liters, 1), "typical_liters": _r(med, 1)})
        for tx in txs:
            if tx.liters > 0 and float(tx.cost) > 0:
                prices[v.fuel_type].append((tx, v, float(tx.cost) / tx.liters))

    for fuel_type, group in prices.items():
        if len(group) < MIN_PRICE_GROUP:
            continue
        med, scale = _robust([p for _, _, p in group])
        for tx, v, price in group:
            if (price - med) / scale > Z_LIMIT and price > med * 1.3:
                add(tx, "high_price", "critical" if price > med * 2 else "warning", f"Price per litre {round((price / med - 1) * 100)}% above typical",
                    f"{v.registration}: {price:.2f} per litre{f' at {tx.station}' if tx.station else ''}, against a typical {med:.2f} for {fuel_type} (no currency).",
                    {"price_per_liter": _r(price), "typical_price_per_liter": _r(med), "fuel_type": fuel_type, "purchases_compared": len(group)})

    items.sort(key=lambda a: (SEVERITY_RANK[a["severity"]], -a["occurred_at"].timestamp()))
    counts = {s: sum(1 for i in items if i["severity"] == s) for s in SEVERITY_RANK}
    return {
        "days": days, "items": items, "counts": counts,
        "stats": {"transactions": len(data.fuel), "vehicles_with_fuel": len(by_vehicle), "screened_for_consumption": screened, "not_enough_history": not_enough},
        "methods": ANOMALY_METHODS, "limitations": ANOMALY_LIMITATIONS,
    }


# -------------------------------------------------------------- delay risk
RISK_METHOD = [
    "A rule-based score from 0 to 99 built from the factors listed on each delivery. It is not a trained prediction model, and the point values are assumptions.",
    "Trip time is estimated from straight-line pickup to destination distance x road factor / average speed + minutes per stop (editable defaults below). Deliveries without coordinates get no trip estimate.",
    "Deliveries without a deadline cannot be assessed. Deliveries already past their deadline are shown as late.",
]


def _driver_late_history(deliveries: list) -> dict:
    """driver_id -> (late, total) over delivered or delayed deliveries that had a deadline."""
    hist: dict = defaultdict(lambda: [0, 0])
    for d in deliveries:
        if d.driver_id is None or d.deadline is None:
            continue
        if d.status == "delivered" and d.delivered_at is not None:
            hist[d.driver_id][1] += 1
            hist[d.driver_id][0] += aware(d.delivered_at) > aware(d.deadline)
        elif d.status == "delayed":
            hist[d.driver_id][1] += 1
            hist[d.driver_id][0] += 1
    return hist


def _minutes(m: float) -> str:
    m = round(abs(m))
    return f"{m // 60} h {m % 60} min" if m >= 120 else f"{m} min"


def delay_risks(data: OrgData, now: datetime, assumptions: Assumptions | None = None, limit: int = 50) -> dict:
    a = assumptions or Assumptions()
    vmap, dmap = data.vehicle_by_id, data.driver_by_id
    history = _driver_late_history(data.deliveries)
    overdue_vehicles = {m.vehicle_id for m in data.maintenance if m.status == "scheduled" and m.scheduled_for and m.scheduled_for < now.date()}
    items, no_deadline = [], 0

    for d in data.deliveries:
        if d.status not in OPEN_DELIVERY:
            continue
        deadline = aware(d.deadline)
        if deadline is None:
            no_deadline += 1
            continue
        left = (deadline - now).total_seconds() / 60
        v, drv = vmap.get(d.vehicle_id), dmap.get(d.driver_id)
        reasons: list[str] = []
        est = None
        if None not in (d.pickup_lat, d.pickup_lng, d.dest_lat, d.dest_lng):
            km = haversine_km((d.pickup_lat, d.pickup_lng), (d.dest_lat, d.dest_lng)) * a.road_factor
            est = km / a.avg_speed_kph * 60 + a.stop_minutes

        if left < 0:
            score, level = 100, "late"
            reasons.append(f"The deadline passed {_minutes(left)} ago and the delivery is not marked delivered")
        else:
            score = 0
            if est is not None and d.status != "in_transit":
                slack = left - est
                if slack < 0:
                    score += 60
                    reasons.append(f"Estimated trip time ({_minutes(est)}) is longer than the time left ({_minutes(left)})")
                elif slack < 60:
                    score += 35
                    reasons.append(f"Only {_minutes(slack)} of slack between the estimated trip ({_minutes(est)}) and the deadline")
                elif slack < 180:
                    score += 15
                    reasons.append(f"Limited slack: {_minutes(slack)} beyond the estimated trip")
            if d.status in ("pending", "assigned") and left < 60:
                score += 25
                reasons.append(f"Not yet in transit with {_minutes(left)} left")
            elif d.status == "in_transit" and left < 30:
                score += 20
                reasons.append(f"Still in transit with {_minutes(left)} left")
            if left < 1440 and d.vehicle_id is None:
                score += 15
                reasons.append("No vehicle assigned and the deadline is within 24 hours")
            if left < 1440 and d.driver_id is None:
                score += 10
                reasons.append("No driver assigned and the deadline is within 24 hours")
            if v is not None and v.status in ("maintenance", "retired"):
                score += 40
                reasons.append(f"Assigned vehicle {v.registration} is {v.status}")
            elif v is not None and v.id in overdue_vehicles:
                score += 10
                reasons.append(f"Assigned vehicle {v.registration} has overdue maintenance")
            if drv is not None and drv.availability in ("off_duty", "on_leave"):
                score += 30
                reasons.append(f"Assigned driver {drv.full_name} is marked {drv.availability.replace('_', ' ')}")
            late_n, total_n = history.get(d.driver_id, (0, 0))
            if drv is not None and total_n >= 5 and late_n / total_n >= 0.3:
                score += 15
                reasons.append(f"{drv.full_name} was late on {late_n} of {total_n} past deliveries")
            score = min(score, 99)
            level = "high" if score >= 60 else "medium" if score >= 30 else "low"

        items.append({
            "delivery_id": str(d.id), "reference": d.reference, "status": d.status, "deadline": deadline, "minutes_left": int(left),
            "estimated_trip_minutes": None if est is None else int(round(est)), "score": score, "level": level, "reasons": reasons,
            "vehicle": v.registration if v else None, "driver": drv.full_name if drv else None, "dest_address": d.dest_address,
        })

    items.sort(key=lambda i: (RISK_RANK[i["level"]], -i["score"], i["minutes_left"]))
    counts = {k: sum(1 for i in items if i["level"] == k) for k in RISK_RANK}
    return {"items": items[:limit], "counts": counts, "open_deliveries": sum(counts.values()), "without_deadline": no_deadline, "methods": RISK_METHOD, "assumptions": a.as_dict()}


# ------------------------------------------------------ maintenance forecast
MAINT_METHOD = [
    "Overdue or upcoming scheduled maintenance is taken from your maintenance records.",
    "Mileage-based service: kilometres since the last completed preventive service (needs an odometer on that record) compared with the service interval below (assumption, default 10,000 km; set it to your own schedule).",
    "Due-date estimate: average daily distance from fuel-purchase odometer readings over the last 90 days (needs readings at least 7 days apart). Without that, no date is given.",
    "Repair frequency: three or more repair records in the last 180 days.",
]


def maintenance_forecast(data: OrgData, now: datetime, interval_km: int = 10_000) -> dict:
    today = now.date()
    items = []
    fuel_by_vehicle: dict = defaultdict(list)
    for f in data.fuel:
        if f.odometer_km is not None:
            fuel_by_vehicle[f.vehicle_id].append((aware(f.occurred_at) or now, f.odometer_km))
    maint_by_vehicle: dict = defaultdict(list)
    for m in data.maintenance:
        maint_by_vehicle[m.vehicle_id].append(m)

    for v in data.vehicles:
        if v.status == "retired":
            continue
        records = maint_by_vehicle.get(v.id, [])
        readings = [o for _, o in fuel_by_vehicle.get(v.id, [])] + [m.odometer_km for m in records if m.odometer_km is not None]
        current = max([v.mileage_km or 0] + readings)
        reasons: list[tuple[int, str]] = []  # (risk 0 high..2 low, text)

        km_day = None
        recent = sorted((t, o) for t, o in fuel_by_vehicle.get(v.id, []) if t >= now - timedelta(days=90))
        if len(recent) >= 2:
            span = (recent[-1][0] - recent[0][0]).total_seconds() / 86400
            if span >= 7 and recent[-1][1] > recent[0][1]:
                km_day = (recent[-1][1] - recent[0][1]) / span

        for m in records:
            if m.status == "scheduled" and m.scheduled_for:
                if m.scheduled_for < today:
                    reasons.append((0, f"Scheduled maintenance is {(today - m.scheduled_for).days} days overdue: {m.description}"))
                elif (m.scheduled_for - today).days <= 14:
                    reasons.append((2, f"Maintenance due in {(m.scheduled_for - today).days} days: {m.description}"))

        done = [m.odometer_km for m in records if m.kind == "preventive" and m.status == "completed" and m.odometer_km is not None]
        since = due_date = None
        if done:
            since = current - max(done)
            ratio = since / interval_km
            if ratio >= 1:
                reasons.append((0, f"{since:,} km since the last preventive service (interval {interval_km:,} km)"))
            elif ratio >= 0.8:
                text = f"{since:,} km since the last preventive service, {interval_km - since:,} km left of the {interval_km:,} km interval"
                if km_day:
                    days_left = (interval_km - since) / km_day
                    due_date = today + timedelta(days=int(days_left))
                    text += f"; at about {km_day:.0f} km/day that is around {due_date.isoformat()}"
                reasons.append((1, text))
        elif current >= interval_km and not any(m.status in ("scheduled", "in_progress") for m in records):
            reasons.append((2, f"No completed preventive service with an odometer is recorded, so mileage-based timing cannot be checked ({current:,} km driven)"))

        cutoff = now - timedelta(days=180)
        repairs = [m for m in records if m.kind == "repair" and m.status != "cancelled" and (aware(m.completed_at) or aware(m.created_at) or now) >= cutoff]
        if len(repairs) >= 3:
            reasons.append((1, f"{len(repairs)} repairs in the last 180 days"))

        if reasons:
            risk = ("high", "medium", "low")[min(r for r, _ in reasons)]
            items.append({
                "vehicle_id": str(v.id), "registration": v.registration, "label": f"{v.manufacturer} {v.model}", "risk": risk,
                "current_km": current, "km_since_service": since, "km_per_day": _r(km_day, 1), "predicted_due_date": due_date,
                "reasons": [t for _, t in sorted(reasons)],
            })
    order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda i: (order[i["risk"]], i["registration"]))
    return {"items": items, "counts": {k: sum(1 for i in items if i["risk"] == k) for k in order}, "interval_km": interval_km, "methods": MAINT_METHOD}


# ----------------------------------------------------------- period metrics
def expiring_documents(data: OrgData, today: date, within_days: int = 30) -> list[dict]:
    soon = today + timedelta(days=within_days)
    out = []

    def check(kind: str, who: str, when: date | None) -> None:
        if when is not None and when <= soon:
            out.append({"item": who, "document": kind, "expires": when, "days_left": (when - today).days, "expired": when < today})

    for v in data.vehicles:
        if v.status != "retired":
            check("insurance", v.registration, v.insurance_expiry)
            check("registration", v.registration, v.registration_expiry)
    for d in data.drivers:
        check("driver license", d.full_name, d.license_expiry)
    out.sort(key=lambda x: x["days_left"])
    return out


def driver_performance(data: OrgData, now: datetime, days: int) -> list[dict]:
    """On-time rate per driver for deliveries delivered in the period (only those that had a deadline)."""
    since = now - timedelta(days=days)
    stats: dict = defaultdict(lambda: [0, 0])  # driver_id -> [on_time, total]
    for d in data.deliveries:
        if d.status != "delivered" or d.driver_id is None or d.deadline is None or d.delivered_at is None:
            continue
        if aware(d.delivered_at) < since:
            continue
        stats[d.driver_id][1] += 1
        stats[d.driver_id][0] += aware(d.delivered_at) <= aware(d.deadline)
    dmap = data.driver_by_id
    rows = [{"driver": dmap[i].full_name, "delivered": t, "on_time": o, "late": t - o, "on_time_rate_pct": round(o / t * 100, 1)} for i, (o, t) in stats.items() if i in dmap]
    rows.sort(key=lambda r: (-r["on_time_rate_pct"], -r["delivered"]))
    return rows


def fuel_stats(data: OrgData, now: datetime, days: int, vehicle_id=None) -> dict:
    since = now - timedelta(days=days)
    vmap = data.vehicle_by_id
    rows = [f for f in data.fuel if (aware(f.occurred_at) or now) >= since and (vehicle_id is None or f.vehicle_id == vehicle_id)]
    per: dict = defaultdict(lambda: {"liters": 0.0, "cost": 0.0, "fills": 0})
    for f in rows:
        p = per[f.vehicle_id]
        p["liters"] += f.liters
        p["cost"] += float(f.cost)
        p["fills"] += 1
    by_vehicle = []
    for vid, p in per.items():
        v = vmap.get(vid)
        by_vehicle.append({"registration": v.registration if v else "unknown", "liters": round(p["liters"], 1), "cost": round(p["cost"], 2), "fills": p["fills"], "cost_per_liter": round(p["cost"] / p["liters"], 3) if p["liters"] > 0 else None})
    by_vehicle.sort(key=lambda r: -r["cost"])
    liters = sum(r["liters"] for r in by_vehicle)
    cost = sum(r["cost"] for r in by_vehicle)
    return {"days": days, "fills": len(rows), "liters": round(liters, 1), "cost": round(cost, 2), "cost_per_liter": round(cost / liters, 3) if liters > 0 else None, "by_vehicle": by_vehicle}


def _pct_change(now_v: float, before: float) -> float | None:
    return round((now_v / before - 1) * 100, 1) if before > 0 else None


def period_facts(data: OrgData, now: datetime, days: int) -> dict:
    """Every number an executive report may use. Nothing here comes from a language model."""
    since, prev_since = now - timedelta(days=days), now - timedelta(days=2 * days)
    today = now.date()
    vstatus = {s: 0 for s in ("active", "idle", "maintenance", "retired")}
    for v in data.vehicles:
        vstatus[v.status] = vstatus.get(v.status, 0) + 1
    dstatus: dict = defaultdict(int)
    for d in data.drivers:
        dstatus[d.availability] += 1

    delivered = [d for d in data.deliveries if d.status == "delivered" and d.delivered_at is not None and aware(d.delivered_at) >= since]
    judged = [d for d in delivered if d.deadline is not None]
    on_time = sum(1 for d in judged if aware(d.delivered_at) <= aware(d.deadline))
    overdue_open = sum(1 for d in data.deliveries if d.status in OPEN_DELIVERY and d.deadline is not None and aware(d.deadline) < now)
    created = sum(1 for d in data.deliveries if (aware(d.created_at) or now) >= since)

    cur, prev = fuel_stats(data, now, days), None
    prev_rows = [f for f in data.fuel if prev_since <= (aware(f.occurred_at) or now) < since]
    prev_cost = sum(float(f.cost) for f in prev_rows)
    prev_liters = sum(f.liters for f in prev_rows)
    prev = {"cost": round(prev_cost, 2), "liters": round(prev_liters, 1), "fills": len(prev_rows)}

    done_m = [m for m in data.maintenance if m.status == "completed" and m.completed_at is not None and aware(m.completed_at) >= since]
    overdue_m = sum(1 for m in data.maintenance if m.status == "scheduled" and m.scheduled_for and m.scheduled_for < today)
    upcoming_m = sum(1 for m in data.maintenance if m.status in ("scheduled", "in_progress") and m.scheduled_for and today <= m.scheduled_for <= today + timedelta(days=14))

    docs = expiring_documents(data, today, 30)
    perf = [p for p in driver_performance(data, now, days) if p["delivered"] >= 3]
    anomalies, risks, forecast = fuel_anomalies(data, now, days), delay_risks(data, now), maintenance_forecast(data, now)

    notes = ["Fuel and maintenance costs have no currency in FleetMind; amounts are as entered."]
    if not data.vehicles and not data.deliveries:
        notes.append("There are no vehicles or deliveries yet, so most figures are zero.")
    if not delivered:
        notes.append("No deliveries were marked delivered in this period.")
    if judged and len(judged) < len(delivered):
        notes.append(f"{len(delivered) - len(judged)} delivered orders had no deadline and are left out of the on-time rate.")
    if not cur["fills"]:
        notes.append("No fuel purchases were recorded in this period.")
    elif not prev["fills"]:
        notes.append("There were no fuel purchases in the previous period, so no fuel comparison is possible.")
    if not perf:
        notes.append("Driver on-time rates need at least 3 delivered orders with deadlines per driver.")

    return {
        "period": {"days": days, "start": since.date().isoformat(), "end": today.isoformat()},
        "fleet": {"vehicles_total": len(data.vehicles), "vehicles_by_status": vstatus, "drivers_total": len(data.drivers), "drivers_by_availability": dict(dstatus)},
        "deliveries": {"created": created, "delivered": len(delivered), "delivered_with_deadline": len(judged), "on_time": on_time, "late_delivered": len(judged) - on_time,
                        "on_time_rate_pct": round(on_time / len(judged) * 100, 1) if judged else None, "open_now": sum(1 for d in data.deliveries if d.status in OPEN_DELIVERY), "open_past_deadline": overdue_open},
        "fuel": {"liters": cur["liters"], "cost": cur["cost"], "fills": cur["fills"], "cost_per_liter": cur["cost_per_liter"], "previous_period": prev,
                  "cost_change_pct": _pct_change(cur["cost"], prev["cost"]), "top_vehicles_by_cost": cur["by_vehicle"][:3]},
        "maintenance": {"completed": len(done_m), "completed_cost": round(sum(float(m.cost or 0) for m in done_m), 2), "overdue_now": overdue_m, "due_next_14_days": upcoming_m},
        "documents": {"expired": sum(1 for x in docs if x["expired"]), "expiring_within_30_days": sum(1 for x in docs if not x["expired"]), "examples": [{"item": x["item"], "document": x["document"], "days_left": x["days_left"]} for x in docs[:5]]},
        "drivers": {"best_on_time": perf[:3], "lowest_on_time": [p for p in sorted(perf, key=lambda r: r["on_time_rate_pct"])[:3] if p["on_time_rate_pct"] < 80]},
        "screening": {
            "fuel_anomalies": anomalies["counts"], "top_fuel_anomalies": [{"title": i["title"], "detail": i["detail"], "severity": i["severity"]} for i in anomalies["items"][:5]],
            "delivery_risk": risks["counts"], "top_delivery_risks": [{"reference": i["reference"], "level": i["level"], "reasons": i["reasons"][:2]} for i in risks["items"] if i["level"] in ("late", "high")][:5],
            "maintenance_risk": forecast["counts"], "top_maintenance_risks": [{"vehicle": i["registration"], "risk": i["risk"], "reasons": i["reasons"][:2]} for i in forecast["items"] if i["risk"] == "high"][:5],
        },
        "data_notes": notes,
    }
