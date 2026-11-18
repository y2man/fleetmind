"""Read-only data tools the assistant may call.

Each tool runs a fixed, parameterized function over the signed-in user's own
organization. The model never writes SQL and never sees other organizations. Tools
are offered only when the user's role can read the underlying data, and results are
trimmed (no emails, phones or licence numbers) and capped in size.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable

from app.core.rbac import permissions_for
from app.services import insights
from app.services.insights import aware

log = logging.getLogger("fleetmind.ai")
MAX_RESULT_CHARS = 14_000


class ToolContext:
    def __init__(self, db, user, now: datetime | None = None):
        self.db, self.user = db, user
        self.now = now or datetime.now(timezone.utc)
        self._data = None
        self.permissions = permissions_for(user.role_name)

    @property
    def data(self) -> insights.OrgData:
        if self._data is None:
            self._data = insights.load(self.db, self.user.organization_id)  # always limited to the user's organization
        return self._data

    def can(self, p: str) -> bool:
        return p in self.permissions


def _int(args: dict, key: str, default: int, lo: int, hi: int) -> int:
    try:
        v = int(args.get(key, default))
    except (TypeError, ValueError):
        v = default
    return max(lo, min(hi, v))


def _choice(args: dict, key: str, allowed: tuple) -> str | None:
    v = args.get(key)
    return v if v in allowed else None


def _text(args: dict, key: str) -> str:
    v = args.get(key)
    return v.strip().lower()[:80] if isinstance(v, str) else ""


def _count(items, key) -> dict:
    out: dict = {}
    for i in items:
        k = key(i)
        out[k] = out.get(k, 0) + 1
    return out


# ------------------------------------------------------------------ tools
def fleet_overview(ctx: ToolContext, a: dict) -> dict:
    d, out = ctx.data, {"as_of": ctx.now.isoformat()}
    if ctx.can("vehicles:read"):
        out["vehicles"] = {"total": len(d.vehicles), "by_status": _count(d.vehicles, lambda v: v.status)}
    if ctx.can("drivers:read"):
        out["drivers"] = {"total": len(d.drivers), "by_availability": _count(d.drivers, lambda x: x.availability)}
    if ctx.can("deliveries:read"):
        out["deliveries"] = {
            "total": len(d.deliveries), "by_status": _count(d.deliveries, lambda x: x.status),
            "open_past_deadline": sum(1 for x in d.deliveries if x.status in insights.OPEN_DELIVERY and x.deadline and aware(x.deadline) < ctx.now),
        }
    return out


def search_vehicles(ctx: ToolContext, a: dict) -> dict:
    d, q = ctx.data, _text(a, "query")
    status, fuel = _choice(a, "status", ("active", "idle", "maintenance", "retired")), _choice(a, "fuel_type", ("diesel", "petrol", "electric", "hybrid", "cng"))
    drivers = d.driver_by_id
    rows = [v for v in d.vehicles if (not status or v.status == status) and (not fuel or v.fuel_type == fuel) and (not q or q in f"{v.registration} {v.manufacturer} {v.model}".lower())]
    rows.sort(key=lambda v: v.registration)
    lim = _int(a, "limit", 20, 1, 50)
    return {"total_matches": len(rows), "returned": min(len(rows), lim), "vehicles": [
        {"registration": v.registration, "make_model": f"{v.manufacturer} {v.model}", "year": v.year, "fuel_type": v.fuel_type, "status": v.status, "mileage_km": v.mileage_km,
         "driver": drivers[v.driver_id].full_name if v.driver_id in drivers else None, "insurance_expiry": v.insurance_expiry, "registration_expiry": v.registration_expiry}
        for v in rows[:lim]]}


def search_drivers(ctx: ToolContext, a: dict) -> dict:
    d, q = ctx.data, _text(a, "query")
    avail = _choice(a, "availability", ("available", "on_duty", "off_duty", "on_leave"))
    rows = [x for x in d.drivers if (not avail or x.availability == avail) and (not q or q in x.full_name.lower())]
    rows.sort(key=lambda x: x.full_name)
    lim = _int(a, "limit", 20, 1, 50)
    by_driver: dict = {}
    for v in d.vehicles:
        if v.driver_id:
            by_driver.setdefault(v.driver_id, []).append(v.registration)
    return {"total_matches": len(rows), "returned": min(len(rows), lim), "drivers": [
        {"name": x.full_name, "availability": x.availability, "safety_score": x.safety_score, "license_expiry": x.license_expiry, "assigned_vehicles": by_driver.get(x.id, [])} for x in rows[:lim]]}


def search_deliveries(ctx: ToolContext, a: dict) -> dict:
    d, q = ctx.data, _text(a, "query")
    status = _choice(a, "status", ("pending", "assigned", "in_transit", "delivered", "delayed", "cancelled"))
    late_only = bool(a.get("late_only"))
    vmap, dmap = d.vehicle_by_id, d.driver_by_id

    def is_late(x) -> bool:
        return x.status == "delayed" or (x.status in insights.OPEN_DELIVERY and x.deadline is not None and aware(x.deadline) < ctx.now) or (
            x.status == "delivered" and x.deadline is not None and x.delivered_at is not None and aware(x.delivered_at) > aware(x.deadline))

    rows = [x for x in d.deliveries if (not status or x.status == status) and (not late_only or is_late(x)) and (not q or q in f"{x.reference} {x.pickup_address} {x.dest_address}".lower())]
    far = datetime.max.replace(tzinfo=timezone.utc)
    rows.sort(key=lambda x: aware(x.deadline) or far)
    lim = _int(a, "limit", 20, 1, 50)
    return {"total_matches": len(rows), "returned": min(len(rows), lim), "deliveries": [
        {"reference": x.reference, "status": x.status, "pickup": x.pickup_address, "destination": x.dest_address, "deadline": x.deadline, "delivered_at": x.delivered_at,
         "late": is_late(x), "vehicle": vmap[x.vehicle_id].registration if x.vehicle_id in vmap else None, "driver": dmap[x.driver_id].full_name if x.driver_id in dmap else None} for x in rows[:lim]]}


def fuel_summary(ctx: ToolContext, a: dict) -> dict:
    d, reg = ctx.data, _text(a, "registration")
    vid = next((v.id for v in d.vehicles if v.registration.lower() == reg), None) if reg else None
    if reg and vid is None:
        return {"error": f"No vehicle with registration '{reg}'."}
    out = insights.fuel_stats(d, ctx.now, _int(a, "days", 30, 1, 365), vid)
    out["note"] = "Costs have no currency. by_vehicle lists the top 10 by cost."
    out["by_vehicle"] = out["by_vehicle"][:10]
    return out


def maintenance_overview(ctx: ToolContext, a: dict) -> dict:
    d, today = ctx.data, ctx.now.date()
    vmap = d.vehicle_by_id
    reg = lambda m: vmap[m.vehicle_id].registration if m.vehicle_id in vmap else None  # noqa: E731
    overdue = [m for m in d.maintenance if m.status == "scheduled" and m.scheduled_for and m.scheduled_for < today]
    upcoming = sorted((m for m in d.maintenance if m.status in ("scheduled", "in_progress") and m not in overdue), key=lambda m: (m.scheduled_for is None, m.scheduled_for or today))
    since = ctx.now - timedelta(days=90)
    done = [m for m in d.maintenance if m.status == "completed" and m.completed_at and aware(m.completed_at) >= since]
    row = lambda m: {"vehicle": reg(m), "kind": m.kind, "description": m.description, "status": m.status, "scheduled_for": m.scheduled_for}  # noqa: E731
    return {"by_status": _count(d.maintenance, lambda m: m.status), "overdue": [row(m) for m in overdue[:10]], "overdue_total": len(overdue),
            "upcoming": [row(m) for m in upcoming[:10]], "completed_last_90_days": len(done), "completed_cost_last_90_days": round(sum(float(m.cost or 0) for m in done), 2), "note": "Costs have no currency."}


def expiring_documents(ctx: ToolContext, a: dict) -> dict:
    rows = insights.expiring_documents(ctx.data, ctx.now.date(), _int(a, "within_days", 30, 1, 365))
    return {"total": len(rows), "documents": rows[:30]}


def driver_performance(ctx: ToolContext, a: dict) -> dict:
    days = _int(a, "days", 30, 1, 365)
    return {"days": days, "drivers": insights.driver_performance(ctx.data, ctx.now, days)[:20], "note": "Only delivered orders that had a deadline are counted."}


def fuel_anomalies(ctx: ToolContext, a: dict) -> dict:
    r = insights.fuel_anomalies(ctx.data, ctx.now, _int(a, "days", 90, 7, 365))
    return {"days": r["days"], "counts": r["counts"], "stats": r["stats"], "top_flags": [{k: i[k] for k in ("severity", "title", "detail", "registration", "occurred_at")} for i in r["items"][:10]], "limitations": r["limitations"]}


def delivery_delay_risks(ctx: ToolContext, a: dict) -> dict:
    r = insights.delay_risks(ctx.data, ctx.now, limit=10)
    return {"counts": r["counts"], "without_deadline": r["without_deadline"], "top": [{k: i[k] for k in ("reference", "level", "score", "minutes_left", "reasons", "vehicle", "driver")} for i in r["items"]], "method": r["methods"][0]}


def maintenance_forecast(ctx: ToolContext, a: dict) -> dict:
    r = insights.maintenance_forecast(ctx.data, ctx.now, _int(a, "interval_km", 10_000, 1000, 100_000))
    return {"interval_km": r["interval_km"], "counts": r["counts"], "vehicles": [{k: i[k] for k in ("registration", "risk", "reasons", "predicted_due_date")} for i in r["items"][:10]], "method": "Mileage and schedule rules from maintenance records; the service interval is an assumption."}


# --------------------------------------------------------------- registry
@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    properties: dict
    permissions: tuple[str, ...]
    run: Callable[[ToolContext, dict], dict]

    def schema(self) -> dict:
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": {"type": "object", "properties": self.properties, "additionalProperties": False}}}


_DAYS = {"type": "integer", "description": "Look-back window in days"}
_LIMIT = {"type": "integer", "description": "Maximum rows to return (1 to 50)"}
TOOLS: list[Tool] = [
    Tool("fleet_overview", "Counts of vehicles by status, drivers by availability and deliveries by status, plus open deliveries past their deadline.", {}, (), fleet_overview),
    Tool("search_vehicles", "List vehicles with status, mileage, assigned driver and document expiry dates. Filter by status, fuel type or text.",
         {"status": {"type": "string", "enum": ["active", "idle", "maintenance", "retired"]}, "fuel_type": {"type": "string", "enum": ["diesel", "petrol", "electric", "hybrid", "cng"]}, "query": {"type": "string", "description": "Matches registration, manufacturer or model"}, "limit": _LIMIT}, ("vehicles:read",), search_vehicles),
    Tool("search_drivers", "List drivers with availability, safety score, licence expiry and assigned vehicles.",
         {"availability": {"type": "string", "enum": ["available", "on_duty", "off_duty", "on_leave"]}, "query": {"type": "string", "description": "Matches the driver's name"}, "limit": _LIMIT}, ("drivers:read",), search_drivers),
    Tool("search_deliveries", "List deliveries with status, deadline, vehicle, driver and whether they are late. Sorted by deadline.",
         {"status": {"type": "string", "enum": ["pending", "assigned", "in_transit", "delivered", "delayed", "cancelled"]}, "late_only": {"type": "boolean"}, "query": {"type": "string", "description": "Matches reference or addresses"}, "limit": _LIMIT}, ("deliveries:read",), search_deliveries),
    Tool("fuel_summary", "Fuel litres, cost and number of fill-ups over a period, in total and per vehicle (top 10 by cost). Costs have no currency.",
         {"days": _DAYS, "registration": {"type": "string", "description": "Optional exact vehicle registration"}}, ("fuel:read",), fuel_summary),
    Tool("maintenance_overview", "Maintenance records by status, overdue and upcoming items, and completed work and cost in the last 90 days.", {}, ("maintenance:read",), maintenance_overview),
    Tool("expiring_documents", "Vehicle insurance and registration and driver licence dates that are expired or expire within a number of days.",
         {"within_days": {"type": "integer", "description": "Window in days (default 30)"}}, ("vehicles:read", "drivers:read"), expiring_documents),
    Tool("driver_performance", "On-time delivery rate per driver over a period (delivered orders with deadlines only).", {"days": _DAYS}, ("drivers:read", "deliveries:read"), driver_performance),
    Tool("fuel_anomalies", "Statistical screening of fuel purchases: unusual consumption, fill sizes, prices and data errors. Flags to review, not proof.", {"days": _DAYS}, ("fuel:read",), fuel_anomalies),
    Tool("delivery_delay_risks", "Rule-based risk of open deliveries missing their deadline, with the reasons for each.", {}, ("deliveries:read",), delivery_delay_risks),
    Tool("maintenance_forecast", "Vehicles likely to need maintenance soon, from overdue items, mileage since last service and repair frequency.",
         {"interval_km": {"type": "integer", "description": "Service interval in km (default 10000)"}}, ("maintenance:read", "vehicles:read"), maintenance_forecast),
]
_BY_NAME = {t.name: t for t in TOOLS}


def tool_schemas(user) -> list[dict]:
    have = permissions_for(user.role_name)
    return [t.schema() for t in TOOLS if all(p in have for p in t.permissions)]


def _default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, (Decimal, uuid.UUID)):
        return float(o) if isinstance(o, Decimal) else str(o)
    return str(o)


def _shrink(out: dict) -> dict:
    """Keep tool output under the size cap by halving its longest lists."""
    out = dict(out)
    while len(json.dumps(out, default=_default)) > MAX_RESULT_CHARS:
        key = max((k for k, v in out.items() if isinstance(v, list) and len(v) > 1), key=lambda k: len(json.dumps(out[k], default=_default)), default=None)
        if key is None:
            return {"error": "The result was too large. Ask a narrower question."}
        out[key] = out[key][: max(1, len(out[key]) // 2)]
        out["truncated"] = True
    return out


def run_tool(ctx: ToolContext, name: str, args: dict) -> str:
    """Run one tool and return JSON text for the model. Never raises."""
    name = name.split(".")[-1].strip()
    tool = _BY_NAME.get(name)
    if tool is None:
        out = {"error": f"Unknown tool '{name[:40]}'. Available: {', '.join(_BY_NAME)}."}
    elif not all(ctx.can(p) for p in tool.permissions):
        out = {"error": "This user's role cannot read that data."}
    else:
        try:
            out = _shrink(tool.run(ctx, args if isinstance(args, dict) else {}))
        except Exception:  # noqa: BLE001 - a failing tool must not break the whole answer
            log.exception("AI tool %s failed", name)
            out = {"error": "The tool failed to run."}
    return json.dumps(out, default=_default)
