"""Smart alerts: rules and statistics over the organization's records, saved as notifications.

"Smart" here means deterministic checks (expiring documents, overdue maintenance, late deliveries)
plus the Phase 7 screening functions (fuel anomalies, delivery delay risk, maintenance risk).
No language model is involved, so alerts are repeatable and each one says why it was raised.

Every alert has a stable dedupe_key built from the condition it describes (for example the
document and its expiry date). A condition is raised once per organization, even if the user has
read or dismissed it; when the underlying fact changes (a new expiry date, a new anomaly) the key
changes and a new alert appears. `build_alerts` is pure; `sync` is the only database writer.
"""
from __future__ import annotations

import hashlib
from datetime import datetime

from app.services import insights
from app.services.insights import OPEN_DELIVERY, SEVERITY_RANK, OrgData, aware

MAX_NEW_PER_RUN = 50   # a first run on a large fleet is spread over several refreshes instead of flooding the bell
MAX_CANDIDATES = 500
FUEL_WINDOW_DAYS = 30
EXPIRY_WINDOW_DAYS = 30


def _key(*parts: object) -> str:
    raw = ":".join(str(p) for p in parts)
    return raw if len(raw) <= 150 else "h:" + hashlib.sha1(raw.encode()).hexdigest()


def _alert(key: str, severity: str, kind: str, title: str, body: str | None, link: str) -> dict:
    return {"key": key, "severity": severity, "kind": kind, "title": title[:160], "body": body, "link": link}


def build_alerts(data: OrgData, now: datetime) -> list[dict]:
    out: list[dict] = []
    today = now.date()
    vmap = data.vehicle_by_id

    for x in insights.expiring_documents(data, today, EXPIRY_WINDOW_DAYS):
        expired = x["expired"]
        title = f"{x['item']}: {x['document']} {'expired' if expired else 'expires soon'}"
        body = f"{'Expired' if expired else 'Expires'} on {x['expires'].isoformat()}" + ("" if expired else f" ({x['days_left']} days left).")
        link = "/app/drivers" if x["document"] == "driver license" else "/app/fleet"
        out.append(_alert(_key("doc", "expired" if expired else "soon", x["document"], x["item"], x["expires"].isoformat()), "critical" if expired else "warning", "document_expiry", title, body, link))

    for m in data.maintenance:
        if m.status == "scheduled" and m.scheduled_for and m.scheduled_for < today:
            v = vmap.get(m.vehicle_id)
            days = (today - m.scheduled_for).days
            out.append(_alert(_key("maint-overdue", m.id), "critical", "maintenance_overdue", f"{v.registration if v else 'Vehicle'}: maintenance overdue",
                              f"{m.description} was scheduled for {m.scheduled_for.isoformat()} ({days} day{'s' if days != 1 else ''} ago).", "/app/maintenance"))

    for d in data.deliveries:
        deadline = aware(d.deadline)
        if d.status == "delayed" or (d.status in OPEN_DELIVERY and deadline is not None and deadline < now):
            out.append(_alert(_key("delivery-late", d.id), "warning", "delivery_late", f"Delivery {d.reference} is late",
                              "Marked delayed." if d.status == "delayed" else f"Past its deadline ({deadline:%Y-%m-%d %H:%M} UTC) and not yet delivered.", "/app/deliveries"))

    for r in insights.delay_risks(data, now, limit=200)["items"]:
        if r["level"] == "high":
            out.append(_alert(_key("delay-risk", r["delivery_id"]), "warning", "delay_risk", f"Delivery {r['reference']} is at high risk of being late",
                              "; ".join(r["reasons"][:2]) or None, "/app/ai"))

    for r in insights.maintenance_forecast(data, now)["items"]:
        if r["risk"] == "high":
            out.append(_alert(_key("maint-risk", r["vehicle_id"]), "warning", "maintenance_risk", f"{r['registration']}: high maintenance risk",
                              "; ".join(r["reasons"][:2]) or None, "/app/ai"))

    for r in insights.fuel_anomalies(data, now, FUEL_WINDOW_DAYS)["items"]:
        out.append(_alert(_key("fuel", r["id"]), r["severity"] if r["severity"] in SEVERITY_RANK else "info", "fuel_anomaly", f"{r['registration']}: {r['title']}", r["detail"], "/app/ai"))

    seen: set[str] = set()
    unique = []
    for a in sorted(out, key=lambda a: SEVERITY_RANK.get(a["severity"], 9)):
        if a["key"] not in seen:
            seen.add(a["key"])
            unique.append(a)
    return unique[:MAX_CANDIDATES]


def sync(db, org_id, now: datetime) -> int:
    """Create notifications for conditions that have not been raised yet. Returns how many were created."""
    from sqlalchemy import select
    from sqlalchemy.exc import IntegrityError

    from app.models import Notification

    candidates = build_alerts(insights.load(db, org_id), now)
    if not candidates:
        return 0
    have = set(db.scalars(select(Notification.dedupe_key).where(Notification.organization_id == org_id, Notification.dedupe_key.in_([c["key"] for c in candidates]))))
    fresh = [c for c in candidates if c["key"] not in have][:MAX_NEW_PER_RUN]
    for c in fresh:
        db.add(Notification(organization_id=org_id, severity=c["severity"], title=c["title"], body=c["body"], kind=c["kind"], link=c["link"], dedupe_key=c["key"]))
    try:
        db.commit()
    except IntegrityError:  # another refresh raised the same alerts at the same moment; nothing is lost
        db.rollback()
        return 0
    return len(fresh)
