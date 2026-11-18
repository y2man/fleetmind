"""CSV and PDF export builders. Pure functions over loaded records (no database access).

CSV safety: spreadsheet programs run cells that start with = + - @ (or tab / carriage return) as
formulas. Free-text cells such as station names or addresses could carry such text from an
attacker, so every text cell that starts with one of those characters gets a leading apostrophe.
Numbers are written as numbers and never altered.
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta

from app.services.analytics import day_start
from app.services.insights import OrgData, aware
from app.services.pdf import Pdf

MAX_ROWS = 50_000
DANGEROUS = ("=", "+", "-", "@", "\t", "\r")

# dataset -> (permission, filename stem)
DATASETS = {
    "vehicles": "vehicles", "drivers": "drivers", "deliveries": "deliveries", "fuel": "fuel", "maintenance": "maintenance",
}


def safe_cell(v: object) -> object:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, datetime):
        return aware(v).isoformat(timespec="seconds")
    if isinstance(v, date):
        return v.isoformat()
    s = str(v)
    return "'" + s if s.startswith(DANGEROUS) else s


def to_csv(headers: list[str], rows: list[list[object]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(headers)
    for r in rows:
        w.writerow([safe_cell(c) for c in r])
    return "\ufeff" + buf.getvalue()  # BOM so Excel opens UTF-8 correctly


def _in_range(dt: datetime | None, start: date, end: date) -> bool:
    dt = aware(dt)
    return dt is not None and day_start(start) <= dt < day_start(end + timedelta(days=1))


def dataset_rows(name: str, data: OrgData, start: date, end: date) -> tuple[list[str], list[list[object]], bool]:
    """Returns (headers, rows, filtered_by_range). Vehicles and drivers are full lists; the rest honor the range."""
    vmap, dmap = data.vehicle_by_id, data.driver_by_id
    reg = lambda vid: vmap[vid].registration if vid in vmap else ""  # noqa: E731
    drv = lambda did: dmap[did].full_name if did in dmap else ""  # noqa: E731

    if name == "vehicles":
        h = ["Registration", "Manufacturer", "Model", "Year", "Fuel type", "Status", "Mileage km", "Capacity kg", "Driver", "Insurance expiry", "Registration expiry"]
        r = [[v.registration, v.manufacturer, v.model, v.year, v.fuel_type, v.status, v.mileage_km, v.capacity_kg, drv(v.driver_id), v.insurance_expiry, v.registration_expiry] for v in sorted(data.vehicles, key=lambda v: v.registration)]
        return h, r, False
    if name == "drivers":
        h = ["Name", "Email", "Phone", "License number", "License expiry", "Availability", "Safety score"]
        r = [[d.full_name, d.email, d.phone, d.license_number, d.license_expiry, d.availability, d.safety_score] for d in sorted(data.drivers, key=lambda d: d.full_name)]
        return h, r, False
    if name == "deliveries":
        h = ["Reference", "Status", "Pickup", "Destination", "Weight kg", "Deadline", "Delivered at", "Vehicle", "Driver", "Created"]
        rows = [d for d in data.deliveries if _in_range(d.created_at, start, end)]
        rows.sort(key=lambda d: aware(d.created_at))
        return h, [[d.reference, d.status, d.pickup_address, d.dest_address, d.weight_kg, d.deadline, d.delivered_at, reg(d.vehicle_id), drv(d.driver_id), d.created_at] for d in rows], True
    if name == "fuel":
        h = ["Date", "Vehicle", "Driver", "Liters", "Cost", "Odometer km", "Station"]
        rows = [f for f in data.fuel if _in_range(f.occurred_at, start, end)]
        rows.sort(key=lambda f: aware(f.occurred_at))
        return h, [[f.occurred_at, reg(f.vehicle_id), drv(f.driver_id), f.liters, float(f.cost), f.odometer_km, f.station] for f in rows], True
    if name == "maintenance":
        h = ["Scheduled for", "Vehicle", "Kind", "Description", "Status", "Cost", "Odometer km", "Completed at"]
        rows = [m for m in data.maintenance if (m.scheduled_for is not None and start <= m.scheduled_for <= end) or (m.scheduled_for is None and _in_range(m.created_at, start, end))]
        rows.sort(key=lambda m: (m.scheduled_for is None, m.scheduled_for or date.max))
        return h, [[m.scheduled_for, reg(m.vehicle_id), m.kind, m.description, m.status, None if m.cost is None else float(m.cost), m.odometer_km, m.completed_at] for m in rows], True
    raise KeyError(name)


# ------------------------------------------------------------------- PDF
def _n(v, digits: int = 0, suffix: str = "") -> str:
    return "–" if v is None else f"{v:,.{digits}f}{suffix}"


def _change(k: dict) -> str:
    c = k["change_pct"]
    return "n/a" if c is None else f"{c:+.1f}%"


def analytics_pdf(report: dict, org_name: str) -> bytes:
    rg = report["range"]
    pdf = Pdf(f"FleetMind analytics {rg['start']} to {rg['end']}")
    pdf.title_block("Fleet analytics report", f"{org_name}  |  {rg['start']} to {rg['end']} ({rg['days']} days, UTC)")

    pdf.heading("Key figures")
    pdf.table(["Measure", "This period", "Previous", "Change"],
              [[k["label"], _n(k["value"], k["decimals"], k["suffix"]), _n(k["previous"], k["decimals"], k["suffix"]), _change(k)] for k in report["kpis"]],
              [4, 2, 2, 1.5], ["l", "r", "r", "r"], size=9)

    s = report["series"]
    pdf.heading(f"Trend ({rg['bucket_days']}-day steps)" if rg["bucket_days"] > 1 else "Trend (daily)")
    pdf.table(["From", "Created", "Completed", "Late", "Fuel cost", "Fuel L", "Maint. cost"],
              [[p["label"], str(p["created"]), str(p["delivered"]), str(p["late"]), _n(p["fuel_cost"], 2), _n(p["liters"], 1), _n(p["maintenance_cost"], 2)] for p in s],
              [2, 1.5, 1.6, 1.2, 2, 1.6, 2], ["l", "r", "r", "r", "r", "r", "r"])

    pdf.heading("Delivery status (created in this period)")
    pdf.table(["Status", "Deliveries"], [[x["status"].replace("_", " ").capitalize(), str(x["count"])] for x in report["delivery_status"]], [3, 1], ["l", "r"])

    pdf.heading("Fuel by vehicle (top 10 by cost)")
    pdf.table(["Vehicle", "Fills", "Liters", "Cost", "Cost / L"],
              [[x["vehicle"], str(x["fills"]), _n(x["liters"], 1), _n(x["cost"], 2), _n(x["cost_per_liter"], 3)] for x in report["fuel_by_vehicle"]],
              [3, 1, 1.5, 2, 1.5], ["l", "r", "r", "r", "r"])

    pdf.heading("Driver on-time performance (top 10 by deliveries)")
    pdf.table(["Driver", "Delivered", "With deadline", "On time", "Late", "On-time rate"],
              [[x["driver"], str(x["delivered"]), str(x["judged"]), str(x["on_time"]), str(x["late"]), _n(x["on_time_rate_pct"], 1, "%")] for x in report["drivers"]],
              [3, 1.4, 1.8, 1.4, 1, 1.8], ["l", "r", "r", "r", "r", "r"])

    pdf.heading("Completed maintenance")
    pdf.table(["Kind", "Records", "Cost"], [[x["kind"].capitalize(), str(x["count"]), _n(x["cost"], 2)] for x in report["maintenance_by_kind"]], [3, 1, 2], ["l", "r", "r"])

    pdf.heading("Notes")
    pdf.bullets(report["notes"])
    return pdf.render()
