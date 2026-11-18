"""Phase 9: the demo data generator. No database needed (the generator and the analytics are pure)."""
from collections import Counter
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS

import pytest

from app.seed.generator import DEMO_USERS, build
from app.services import alerts, insights

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)
VEHICLE_STATUS = {"active", "idle", "maintenance", "retired"}
DELIVERY_STATUS = {"pending", "assigned", "in_transit", "delivered", "delayed", "cancelled"}
DRIVER_STATUS = {"available", "on_duty", "off_duty", "on_leave"}
MAINT_STATUS = {"scheduled", "in_progress", "completed", "cancelled"}


@pytest.fixture(scope="module")
def data():
    return build(now=NOW)


def org_data(d):
    rows = lambda xs: [NS(**x) for x in xs]  # noqa: E731
    return insights.OrgData(rows(d.vehicles), rows(d.drivers), rows(d.deliveries), rows(d.fuel), rows(d.maintenance))


def test_same_inputs_give_identical_data():
    a, b = build(7, NOW), build(7, NOW)
    assert a.counts() == b.counts()
    assert [d["reference"] for d in a.deliveries] == [d["reference"] for d in b.deliveries]
    assert [f["liters"] for f in a.fuel] == [f["liters"] for f in b.fuel]
    assert build(8, NOW).fuel[0]["liters"] != a.fuel[0]["liters"] or build(8, NOW).fuel[5]["liters"] != a.fuel[5]["liters"]


def test_expected_volume(data):
    c = data.counts()
    assert c["vehicles"] == 14 and c["drivers"] == 12 and c["geofences"] == 3
    assert 120 <= c["deliveries"] <= 300 and 150 <= c["fuel"] <= 400 and c["maintenance"] >= 15
    assert c["routes"] >= 3 and c["stops"] >= c["routes"] * 3


def test_unique_values_per_organization(data):
    for rows, key in ((data.vehicles, "registration"), (data.drivers, "license_number"), (data.deliveries, "reference"), (data.geofences, "name")):
        values = [r[key] for r in rows]
        assert len(values) == len(set(values)), key
    ids = [r["id"] for rows in (data.drivers, data.vehicles, data.deliveries, data.fuel, data.maintenance, data.routes, data.stops) for r in rows]
    assert len(ids) == len(set(ids))
    assert len({(s["route_id"], s["sequence"]) for s in data.stops}) == len(data.stops)


def test_references_resolve(data):
    drivers, vehicles = {d["id"] for d in data.drivers}, {v["id"] for v in data.vehicles}
    routes, deliveries = {r["id"] for r in data.routes}, {d["id"] for d in data.deliveries}
    assert all(v["driver_id"] in drivers for v in data.vehicles if v["driver_id"])
    for d in data.deliveries:
        assert d["vehicle_id"] is None or d["vehicle_id"] in vehicles
        assert d["driver_id"] is None or d["driver_id"] in drivers
        assert d.get("route_id") is None or d["route_id"] in routes
    assert all(f["vehicle_id"] in vehicles for f in data.fuel) and all(m["vehicle_id"] in vehicles for m in data.maintenance)
    assert all(s["route_id"] in routes and (s["delivery_id"] is None or s["delivery_id"] in deliveries) for s in data.stops)


def test_values_are_valid_for_the_database_constraints(data):
    assert {v["status"] for v in data.vehicles} <= VEHICLE_STATUS
    assert {d["status"] for d in data.deliveries} <= DELIVERY_STATUS
    assert {d["availability"] for d in data.drivers} <= DRIVER_STATUS
    assert {m["status"] for m in data.maintenance} <= MAINT_STATUS
    assert {m["kind"] for m in data.maintenance} <= {"preventive", "repair", "inspection"}
    assert {v["fuel_type"] for v in data.vehicles} <= {"diesel", "petrol", "electric", "hybrid", "cng"}
    assert all(f["liters"] > 0 and f["cost"] > 0 for f in data.fuel)
    assert all(0 <= d["safety_score"] <= 100 for d in data.drivers)
    for rows in (data.drivers, data.vehicles, data.deliveries, data.fuel, data.maintenance):
        assert all(r["is_demo"] is True for r in rows)  # demo rows must always be flagged


def test_dates_are_consistent_and_relative_to_now(data):
    for d in data.deliveries:
        assert d["created_at"].tzinfo is not None and d["deadline"] > d["created_at"]
        if d["status"] == "delivered":
            assert d["delivered_at"] is not None and d["delivered_at"] >= d["created_at"]
            assert d["delivered_at"] <= NOW + timedelta(seconds=1)
        else:
            assert d["delivered_at"] is None
    assert min(d["created_at"] for d in data.deliveries) >= NOW - timedelta(days=91)
    assert max(d["created_at"] for d in data.deliveries) <= NOW + timedelta(days=7)
    assert all(f["occurred_at"] <= NOW for f in data.fuel)
    later = build(7, NOW + timedelta(days=30))  # re-seeding a month later shifts every date forward
    assert max(f["occurred_at"] for f in later.fuel) > NOW + timedelta(days=20)


def test_coordinates_are_in_addis_ababa(data):
    for d in data.deliveries:
        for lat, lng in ((d["pickup_lat"], d["pickup_lng"]), (d["dest_lat"], d["dest_lng"])):
            assert 8.85 < lat < 9.10 and 38.65 < lng < 38.95


def test_routes_are_estimates_with_assumptions(data):
    for r in data.routes:
        assert r["total_distance_km"] > 0 and r["optimization_notes"]["estimates"] is True
        assert "assumptions" in r["optimization_notes"]


def test_demo_accounts_cover_every_role_and_are_valid_logins():
    assert {u["role_name"] for u in DEMO_USERS} == {"owner", "admin", "dispatcher", "viewer"}
    assert len({u["email"] for u in DEMO_USERS}) == 4
    pytest.importorskip("email_validator")
    from app.schemas.auth import LoginIn

    from app.seed.generator import DEMO_PASSWORD
    for u in DEMO_USERS:
        LoginIn(email=u["email"], password=DEMO_PASSWORD)


def test_planted_problems_are_found_by_the_real_alert_and_screening_code(data):
    d = org_data(data)
    found = Counter((a["severity"], a["kind"]) for a in alerts.build_alerts(d, NOW))
    assert found[("critical", "document_expiry")] == 2        # expired insurance and expired licence
    assert found[("warning", "document_expiry")] == 2        # registration and licence expiring soon
    assert found[("critical", "maintenance_overdue")] == 1
    assert found[("warning", "delivery_late")] >= 2
    kinds = Counter((i["registration"], i["kind"]) for i in insights.fuel_anomalies(d, NOW)["items"])
    assert kinds[("ET-A1001", "large_fill")] == 1
    assert kinds[("ET-A1005", "possible_duplicate")] == 1
    assert kinds[("ET-A1005", "odometer_regression")] == 1


def test_clean_vehicles_raise_no_fuel_flags(data):
    flagged = {i["registration"] for i in insights.fuel_anomalies(org_data(data), NOW)["items"]}
    assert flagged <= {"ET-A1001", "ET-A1005"}  # only the two vehicles with planted problems


def test_planted_list_documents_what_was_planted(data):
    assert len(data.planted) >= 8 and any("insurance expired" in p for p in data.planted)
