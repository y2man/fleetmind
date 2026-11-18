"""Builds a realistic demo fleet as plain dictionaries. No database, no web framework.

Everything is derived from a seed number and a reference time ("now"), so the same inputs always
give the same data and the dates always sit relative to today (a fleet seeded today looks current).
The data is fictional: invented companies, drivers and plates, with approximate Addis Ababa
coordinates. Records are written with is_demo=True by runner.py.

The set deliberately contains a few problems so that alerts, the AI screening and the dashboard
have something real to show: an expired insurance date, a document expiring soon, an overdue
maintenance task, late deliveries, and three fuel entries that look wrong (a duplicate, an
odometer that goes backwards, an unusually large fill). They are listed in `SeedData.planted`.
"""
from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from app.services.routing import Assumptions, plan

DEMO_ORG_NAME = "Selam Freight (Demo)"
DEMO_PASSWORD = "FleetMind-Demo-2026"  # public on purpose: this is demo data, see docs/SEED.md
DEMO_USERS = [
    {"email": "owner@example.com", "full_name": "Demo Owner", "role_name": "owner"},
    {"email": "admin@example.com", "full_name": "Demo Admin", "role_name": "admin"},
    {"email": "dispatcher@example.com", "full_name": "Demo Dispatcher", "role_name": "dispatcher"},
    {"email": "viewer@example.com", "full_name": "Demo Viewer", "role_name": "viewer"},
]

HISTORY_DAYS = 90
FUTURE_DAYS = 6

# name, lat, lng: approximate, for a demo map only
PLACES = [
    ("Bole", 8.9806, 38.7992), ("Kazanchis", 9.0192, 38.7637), ("Piassa", 9.0350, 38.7469),
    ("Merkato", 9.0108, 38.7358), ("Sarbet", 8.9916, 38.7285), ("Lideta", 9.0089, 38.7311),
    ("Gerji", 9.0000, 38.8100), ("Megenagna", 9.0206, 38.8006), ("CMC", 9.0170, 38.8260),
    ("Ayat", 9.0270, 38.8680), ("Summit", 9.0010, 38.8330), ("Gullele", 9.0560, 38.7290),
]
DEPOTS = [("Bole Depot", 8.9760, 38.7870), ("Kality Warehouse", 8.9540, 38.7620), ("Akaki Logistics Park", 8.9330, 38.7850)]
CARGO = ["Pallets of bottled water", "Office furniture", "Packaged food", "Construction fittings", "Pharmacy supplies",
         "Electronics", "Textiles", "Printing paper", "Spare parts", "Retail stock", "Cleaning products", "Agricultural inputs"]
FIRST = ["Abebe", "Hana", "Dawit", "Meron", "Samuel", "Selamawit", "Yonas", "Tigist", "Bereket", "Liya", "Henok", "Rahel", "Mulugeta", "Saron"]
LAST = ["Tesfaye", "Bekele", "Alemu", "Girma", "Haile", "Mengistu", "Tadesse", "Wolde", "Kebede", "Desta", "Negash", "Assefa", "Gebre", "Lemma"]
STATIONS = ["Total Bole", "NOC Kazanchis", "Oilibya Megenagna", "Total Kality", "NOC Sarbet", "Oilibya Lideta"]

# registration, manufacturer, model, year, fuel, status, capacity_kg, l_per_100km, km_per_day
VEHICLE_SPECS = [
    ("ET-A1001", "Isuzu", "NPR", 2021, "diesel", "active", 3500, 17.0, 120),
    ("ET-A1002", "Isuzu", "NPR", 2020, "diesel", "active", 3500, 17.5, 110),
    ("ET-A1003", "Hino", "300", 2022, "diesel", "active", 4000, 18.5, 105),
    ("ET-A1004", "Mitsubishi", "Canter", 2019, "diesel", "active", 3000, 16.0, 100),
    ("ET-A1005", "Toyota", "Hilux", 2022, "diesel", "active", 1000, 10.5, 140),
    ("ET-A1006", "Toyota", "Hilux", 2021, "diesel", "active", 1000, 10.8, 135),
    ("ET-A1007", "Ford", "Transit", 2020, "diesel", "active", 1500, 11.5, 130),
    ("ET-A1008", "Nissan", "Urvan", 2018, "petrol", "active", 1200, 12.5, 125),
    ("ET-A1009", "Toyota", "Hiace", 2021, "petrol", "idle", 1100, 11.8, 90),
    ("ET-A1010", "Isuzu", "FRR", 2017, "diesel", "idle", 6000, 21.0, 80),
    ("ET-A1011", "Hyundai", "H100", 2019, "diesel", "idle", 1000, 10.2, 95),
    ("ET-A1012", "Hino", "500", 2018, "diesel", "maintenance", 8000, 24.0, 85),
    ("ET-A1013", "Mitsubishi", "Canter", 2016, "diesel", "maintenance", 3000, 16.5, 80),
    ("ET-A1014", "Ford", "Ranger", 2015, "diesel", "retired", 900, 11.0, 0),
]
FUEL_PRICE = {"diesel": 1.15, "petrol": 1.25}  # per litre, no currency (FleetMind stores none)
WRITTEN_OFF = "retired"


@dataclass
class SeedData:
    drivers: list[dict] = field(default_factory=list)
    vehicles: list[dict] = field(default_factory=list)
    deliveries: list[dict] = field(default_factory=list)
    fuel: list[dict] = field(default_factory=list)
    maintenance: list[dict] = field(default_factory=list)
    routes: list[dict] = field(default_factory=list)
    stops: list[dict] = field(default_factory=list)
    geofences: list[dict] = field(default_factory=list)
    planted: list[str] = field(default_factory=list)  # human-readable list of the deliberate problems

    def counts(self) -> dict[str, int]:
        return {k: len(getattr(self, k)) for k in ("drivers", "vehicles", "deliveries", "fuel", "maintenance", "routes", "stops", "geofences")}


def _id(rng: random.Random) -> uuid.UUID:
    return uuid.UUID(int=rng.getrandbits(128), version=4)


def _at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=timezone.utc)


def _jitter(rng: random.Random, p: tuple[float, float], meters: float = 400) -> tuple[float, float]:
    d = meters / 111_320
    return round(p[0] + rng.uniform(-d, d), 6), round(p[1] + rng.uniform(-d, d), 6)


def _drivers(rng: random.Random, today: date, out: SeedData) -> None:
    names: set[str] = set()
    for i in range(12):
        while True:
            name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
            if name not in names:
                names.add(name)
                break
        status = "on_leave" if i == 11 else "off_duty" if i == 10 else "on_duty" if i < 7 else "available"
        out.drivers.append({
            "id": _id(rng), "full_name": name, "license_number": f"ETH-DL-{48100 + i * 37}",
            "email": f"driver{i + 1}@example.com", "phone": f"+2519{rng.randint(10000000, 99999999)}",
            "license_expiry": today + timedelta(days=rng.randint(120, 900)),
            "availability": status, "safety_score": round(rng.uniform(78, 98), 1), "is_demo": True,
        })
    out.drivers[3]["license_expiry"] = today + timedelta(days=18)       # expiring soon -> warning
    out.drivers[8]["license_expiry"] = today - timedelta(days=9)        # expired -> critical
    out.planted += [f"Driver {out.drivers[3]['full_name']}: licence expires in 18 days",
                    f"Driver {out.drivers[8]['full_name']}: licence expired 9 days ago"]


def _vehicles(rng: random.Random, today: date, out: SeedData) -> dict:
    meta: dict = {}
    for i, (reg, make, model, year, fuel, status, cap, l100, kmday) in enumerate(VEHICLE_SPECS):
        age = max(1, today.year - year)
        mileage = int(age * rng.randint(20000, 32000) + rng.randint(0, 4000))
        vid = _id(rng)
        driver = out.drivers[i]["id"] if i < 10 and status != "retired" else None
        out.vehicles.append({
            "id": vid, "registration": reg, "manufacturer": make, "model": model, "year": year, "fuel_type": fuel,
            "status": status, "mileage_km": mileage, "capacity_kg": cap, "driver_id": driver,
            "insurance_expiry": today + timedelta(days=rng.randint(70, 330)),
            "registration_expiry": today + timedelta(days=rng.randint(70, 330)), "is_demo": True,
        })
        meta[vid] = {"l100": l100, "kmday": kmday, "i": i}
    out.vehicles[2]["insurance_expiry"] = today - timedelta(days=12)    # expired -> critical
    out.vehicles[5]["registration_expiry"] = today + timedelta(days=9)  # expiring soon -> warning
    out.planted += [f"Vehicle {out.vehicles[2]['registration']}: insurance expired 12 days ago",
                    f"Vehicle {out.vehicles[5]['registration']}: registration expires in 9 days"]
    return meta


def _deliveries(rng: random.Random, today: date, now: datetime, out: SeedData) -> None:
    on_road = [v for v in out.vehicles if v["status"] == "active"]
    seq = 1000
    for offset in range(-HISTORY_DAYS, FUTURE_DAYS + 1):
        day = today + timedelta(days=offset)
        if day.weekday() == 6 and offset < 0:  # Sundays are quiet
            count = rng.randint(0, 1)
        else:
            count = rng.randint(1, 3) + (1 if rng.random() < 0.25 else 0)
        for _ in range(count):
            seq += 1
            v = rng.choice(on_road)
            pickup_name, plat, plng = rng.choice(DEPOTS)
            dest_name, dlat, dlng = rng.choice(PLACES)
            plat, plng = _jitter(rng, (plat, plng), 150)
            dlat, dlng = _jitter(rng, (dlat, dlng), 500)
            created = _at(day, rng.randint(6, 10), rng.randint(0, 59))
            deadline = created + timedelta(hours=rng.randint(4, 9))
            row = {
                "id": _id(rng), "reference": f"D-{seq}", "description": rng.choice(CARGO), "weight_kg": float(rng.randint(80, 900)),
                "pickup_address": f"{pickup_name}, Addis Ababa", "pickup_lat": plat, "pickup_lng": plng,
                "dest_address": f"{dest_name}, Addis Ababa", "dest_lat": dlat, "dest_lng": dlng,
                "deadline": deadline, "delivered_at": None, "vehicle_id": v["id"], "driver_id": v["driver_id"],
                "created_at": created, "updated_at": created, "is_demo": True,
            }
            if offset >= 1:                                  # tomorrow onwards: not started
                row["status"] = "assigned" if rng.random() < 0.6 else "pending"
                if row["status"] == "pending":
                    row["vehicle_id"] = row["driver_id"] = None
            elif offset == 0:                                # today
                row["status"] = rng.choice(["in_transit", "in_transit", "assigned", "delivered"])
                if row["status"] == "delivered":
                    row["delivered_at"] = min(now, deadline - timedelta(minutes=rng.randint(10, 90)))
                    if row["delivered_at"] < created:
                        row["delivered_at"] = created + timedelta(minutes=30)
            else:                                            # history
                roll = rng.random()
                if roll < 0.03:
                    row["status"] = "cancelled"
                    row["vehicle_id"] = row["driver_id"] = None
                elif roll < 0.07:
                    row["status"] = "delayed"                # still marked delayed, never closed
                elif roll < 0.15:
                    row["status"] = "delivered"              # delivered, but after the deadline
                    row["delivered_at"] = deadline + timedelta(minutes=rng.randint(15, 180))
                else:
                    row["status"] = "delivered"
                    row["delivered_at"] = deadline - timedelta(minutes=rng.randint(10, 200))
                    if row["delivered_at"] < created:
                        row["delivered_at"] = created + timedelta(minutes=45)
            if row["delivered_at"]:
                row["updated_at"] = row["delivered_at"]
            out.deliveries.append(row)
    # Guarantee two open deliveries whose deadline has already passed (late-delivery alerts),
    # whatever the random draw gave: reopen two recent ones that were past their deadline.
    def late_open(r: dict) -> bool:
        return r["status"] in ("assigned", "in_transit") and r["deadline"] < now
    if sum(1 for r in out.deliveries if late_open(r)) < 2:
        recent = [r for r in out.deliveries if r["deadline"] < now and r["created_at"].date() >= today - timedelta(days=2) and r["vehicle_id"]]
        for r in recent[-2:]:
            r.update(status="in_transit", delivered_at=None)
    out.planted.append("Several deliveries are past their deadline and not delivered, plus some marked delayed")


def _fuel(rng: random.Random, today: date, now: datetime, out: SeedData, meta: dict) -> None:
    for v in out.vehicles:
        m = meta[v["id"]]
        if v["status"] == "retired":
            continue
        days_active = 25 if v["status"] == "maintenance" else HISTORY_DAYS
        gap_days = 4 + (m["i"] % 3)
        # work backwards from today's odometer so the readings end at the vehicle's current mileage
        odo = v["mileage_km"]
        stamps: list[datetime] = []
        d = 0.5
        while d < days_active:
            stamps.append(now - timedelta(days=d, hours=rng.randint(0, 5)))
            d += gap_days + rng.choice([-1, 0, 0, 1])
        rows = []
        for ts in stamps:  # newest first
            km = m["kmday"] * gap_days * rng.uniform(0.85, 1.15)
            liters = round(km * m["l100"] / 100 * rng.uniform(0.94, 1.06), 1)
            price = FUEL_PRICE[v["fuel_type"]] * (1 + 0.03 * rng.uniform(-1, 1) + 0.0004 * (HISTORY_DAYS - (now - ts).days))
            rows.append({"id": _id(rng), "vehicle_id": v["id"], "driver_id": v["driver_id"], "liters": liters,
                         "cost": round(liters * price, 2), "odometer_km": int(odo), "station": rng.choice(STATIONS),
                         "occurred_at": ts, "is_demo": True})
            odo -= km
        out.fuel += rows
    # planted anomalies on the first two active vehicles
    by_v: dict = {}
    for f in out.fuel:
        by_v.setdefault(f["vehicle_id"], []).append(f)
    a, b = out.vehicles[0], out.vehicles[4]
    fa = sorted(by_v[a["id"]], key=lambda x: x["occurred_at"], reverse=True)
    fb = sorted(by_v[b["id"]], key=lambda x: x["occurred_at"], reverse=True)
    big = fa[2]                                                   # an unusually large fill
    big["liters"] = round(big["liters"] * 2.6, 1)
    big["cost"] = round(big["liters"] * FUEL_PRICE["diesel"], 2)
    dup = dict(fb[3], id=_id(rng), occurred_at=fb[3]["occurred_at"] + timedelta(minutes=25), station=fb[3]["station"])
    out.fuel.append(dup)                                          # same purchase entered twice
    fb[5]["odometer_km"] = int(fb[5]["odometer_km"] - 900)        # a typing mistake: this reading is lower than the one before it
    out.planted += [f"{a['registration']}: one fuel fill is about 2.6x its normal size",
                    f"{b['registration']}: a fuel purchase entered twice 25 minutes apart",
                    f"{b['registration']}: one odometer reading typed 900 km too low (goes backwards)"]


def _maintenance(rng: random.Random, today: date, now: datetime, out: SeedData, meta: dict) -> None:
    def rec(v, kind, desc, status, cost, odo, scheduled, completed=None):
        out.maintenance.append({
            "id": _id(rng), "vehicle_id": v["id"], "kind": kind, "description": desc, "status": status,
            "cost": cost, "odometer_km": odo, "scheduled_for": scheduled, "completed_at": completed,
            "created_at": now - timedelta(days=60), "updated_at": now, "is_demo": True,
        })

    for v in out.vehicles:
        if v["status"] == "retired":
            continue
        i = meta[v["id"]]["i"]
        done_odo = v["mileage_km"] - rng.randint(2500, 9000)
        done_at = now - timedelta(days=rng.randint(20, 75))
        rec(v, "preventive", "Oil and filter service", "completed", round(rng.uniform(80, 180), 2), done_odo, done_at.date(), done_at)
        if i % 3 == 0:
            d = now - timedelta(days=rng.randint(5, 40))
            rec(v, "repair", rng.choice(["Brake pad replacement", "Alternator replacement", "Tyre replacement (2)", "Clutch adjustment"]),
                "completed", round(rng.uniform(150, 620), 2), v["mileage_km"] - rng.randint(500, 3000), d.date(), d)
        if i % 4 == 1:
            rec(v, "inspection", "Annual roadworthiness inspection", "scheduled", None, None, today + timedelta(days=rng.randint(8, 50)))
        if v["status"] == "maintenance":
            rec(v, "repair", "Gearbox overhaul" if i == 11 else "Engine cooling system repair", "in_progress", None, v["mileage_km"], today - timedelta(days=3))
    ov = out.vehicles[6]
    rec(ov, "preventive", "Brake inspection and service", "scheduled", None, None, today - timedelta(days=6))
    rec(out.vehicles[1], "preventive", "Scheduled 10,000 km service", "scheduled", None, None, today + timedelta(days=4))
    out.planted.append(f"Vehicle {ov['registration']}: a scheduled service is 6 days overdue")


def _routes(rng: random.Random, now: datetime, out: SeedData) -> None:
    by_day: dict = {}
    for d in out.deliveries:
        if d["vehicle_id"] and d["status"] != "cancelled":
            by_day.setdefault((d["created_at"].date(), d["vehicle_id"]), []).append(d)
    groups = [g for g in by_day.items() if len(g[1]) >= 2 and g[0][0] <= now.date()]  # past and today only
    groups.sort(key=lambda g: g[0][0], reverse=True)
    for n, ((day, vid), ds) in enumerate(groups[:5]):
        ds = ds[:4]
        pts = [(ds[0]["pickup_lat"], ds[0]["pickup_lng"])] + [(x["dest_lat"], x["dest_lng"]) for x in ds]
        result = plan(pts, Assumptions())
        rid = _id(rng)
        status = "in_progress" if day == now.date() else "completed"
        out.routes.append({
            "id": rid, "name": f"Route {day:%d %b} - {out.vehicles[[v['id'] for v in out.vehicles].index(vid)]['registration']}", "status": status,
            "vehicle_id": vid, "driver_id": ds[0]["driver_id"], "total_distance_km": result["optimized"]["distance_km"],
            "est_duration_min": result["optimized"]["duration_min"],
            "optimization_notes": {k: result[k] for k in ("original", "optimized", "saved", "saved_percent", "assumptions")} | {"optimized": True, "estimates": True},
            "created_at": _at(day, 6, 30), "updated_at": _at(day, 6, 30),
        })
        for seq, idx in enumerate(result["order"]):
            if idx == 0:
                addr, lat, lng, did = ds[0]["pickup_address"], pts[0][0], pts[0][1], None
            else:
                x = ds[idx - 1]
                addr, lat, lng, did = x["dest_address"], x["dest_lat"], x["dest_lng"], x["id"]
            for x in ds:
                if did and x["id"] == did:
                    x["route_id"] = rid
            out.stops.append({"id": _id(rng), "route_id": rid, "sequence": seq, "address": addr, "lat": lat, "lng": lng,
                              "eta": _at(day, 7 + seq, (seq * 17) % 60), "delivery_id": did})


def _geofences(out: SeedData) -> None:
    out.geofences += [
        {"name": "Bole Depot", "center_lat": 8.9760, "center_lng": 38.7870, "radius_m": 600.0, "is_active": True},
        {"name": "Merkato market zone", "center_lat": 9.0108, "center_lng": 38.7358, "radius_m": 900.0, "is_active": True},
        {"name": "Kality industrial area", "center_lat": 8.9540, "center_lng": 38.7620, "radius_m": 1200.0, "is_active": True},
    ]


def build(seed: int = 20260101, now: datetime | None = None) -> SeedData:
    """Build the demo data set. `now` defaults to the current UTC time."""
    now = now or datetime.now(timezone.utc)
    today = now.date()
    rng = random.Random(seed)
    out = SeedData()
    _drivers(rng, today, out)
    meta = _vehicles(rng, today, out)
    _deliveries(rng, today, now, out)
    _fuel(rng, today, now, out, meta)
    _maintenance(rng, today, now, out, meta)
    _routes(rng, now, out)
    _geofences(out)
    return out
