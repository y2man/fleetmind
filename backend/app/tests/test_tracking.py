import random
import uuid

import pytest
from starlette.websockets import WebSocketDisconnect

from app.services import routing
from app.services.live import OrgState, run_tick
from tests.conftest import auth, invite_and_login, register

V = {"registration": "ET-2001", "manufacturer": "Isuzu", "model": "NPR", "status": "active"}
GF = {"name": "Depot", "center_lat": 9.03, "center_lng": 38.74, "radius_m": 500}
STOPS = [
    {"address": "Depot", "lat": 9.0, "lng": 38.7},
    {"address": "Far", "lat": 9.1, "lng": 38.9},
    {"address": "Near 1", "lat": 9.01, "lng": 38.71},
    {"address": "Far 2", "lat": 9.09, "lng": 38.88},
    {"address": "Near 2", "lat": 9.02, "lng": 38.72},
]


def owner(client, email="owner@a.com", org="Acme"):
    return auth(register(client, email, org)["access_token"])


# ------------------------------------------------------------ pure planning
def test_plan_orders_stops_and_keeps_start_first():
    pts = [(s["lat"], s["lng"]) for s in STOPS]
    r = routing.plan(pts)
    assert r["order"][0] == 0 and sorted(r["order"]) == list(range(5))
    assert r["optimized"]["distance_km"] <= r["original"]["distance_km"]
    assert r["saved"]["distance_km"] >= 0 and r["assumptions"]["road_factor"] == 1.3
    assert routing.plan([(1, 1), (2, 2)])["order"] == [0, 1]


# --------------------------------------------------------------- geofences
def test_geofence_crud_validation_and_conflict(client):
    h = owner(client)
    r = client.post("/api/v1/geofences", json=GF, headers=h)
    assert r.status_code == 201, r.text
    gid = r.json()["id"]
    assert client.post("/api/v1/geofences", json=GF, headers=h).status_code == 409
    assert client.post("/api/v1/geofences", json={**GF, "name": "Bad", "radius_m": 0}, headers=h).status_code == 422
    assert client.post("/api/v1/geofences", json={**GF, "name": "Bad", "center_lat": 120}, headers=h).status_code == 422
    assert client.patch(f"/api/v1/geofences/{gid}", json={"radius_m": 900, "is_active": False}, headers=h).json()["radius_m"] == 900
    assert client.delete(f"/api/v1/geofences/{gid}", headers=h).status_code == 204
    assert client.get(f"/api/v1/geofences/{gid}", headers=h).status_code == 404


def test_geofence_isolation_and_permissions(client):
    o = register(client)["access_token"]
    other = owner(client, "b@b.com", "Beta")
    gid = client.post("/api/v1/geofences", json=GF, headers=auth(o)).json()["id"]
    assert client.get(f"/api/v1/geofences/{gid}", headers=other).status_code == 404
    assert client.get("/api/v1/geofences", headers=other).json()["total"] == 0
    viewer = invite_and_login(client, o, "v@a.com", "viewer")
    disp = invite_and_login(client, o, "d@a.com", "dispatcher")
    assert client.get("/api/v1/geofences", headers=auth(viewer)).status_code == 200
    assert client.post("/api/v1/geofences", json={**GF, "name": "V"}, headers=auth(viewer)).status_code == 403
    assert client.post("/api/v1/geofences", json={**GF, "name": "D"}, headers=auth(disp)).status_code == 201


# ------------------------------------------------------------------- routes
def test_plan_preview_does_not_save(client):
    h = owner(client)
    r = client.post("/api/v1/routes/plan", json={"stops": STOPS}, headers=h)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["stops"][0]["address"] == "Depot" and len(j["stops"]) == 5
    assert j["saved_percent"] > 0 and "road_factor" in j["assumptions"]
    assert client.get("/api/v1/routes", headers=h).json()["total"] == 0


def test_plan_assumptions_are_used_and_validated(client):
    h = owner(client)
    ok = client.post("/api/v1/routes/plan", json={"stops": STOPS, "assumptions": {"road_factor": 1.0}}, headers=h).json()
    base = client.post("/api/v1/routes/plan", json={"stops": STOPS}, headers=h).json()
    assert ok["optimized"]["distance_km"] < base["optimized"]["distance_km"]
    assert ok["assumptions"]["road_factor"] == 1.0
    assert client.post("/api/v1/routes/plan", json={"stops": STOPS[:1]}, headers=h).status_code == 422
    assert client.post("/api/v1/routes/plan", json={"stops": STOPS, "assumptions": {"avg_speed_kph": 0}}, headers=h).status_code == 422


def test_plan_uses_osrm_road_matrix_when_configured(client, monkeypatch):
    from app.core.config import get_settings
    from app.services import routing

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "code": "Ok",
                "distances": [
                    [0, 9000, 1000],
                    [9000, 0, 1000],
                    [1000, 1000, 0],
                ],
                "durations": [
                    [0, 900, 120],
                    [900, 0, 120],
                    [120, 120, 0],
                ],
            }

    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr(get_settings(), "osrm_base_url", "https://osrm.example.test")
    monkeypatch.setattr(routing.httpx, "get", fake_get)
    h = owner(client)
    result = client.post(
        "/api/v1/routes/plan",
        headers=h,
        json={"stops": STOPS[:3]},
    )
    assert result.status_code == 200, result.text
    assert result.json()["assumptions"]["routing_provider"] == "OSRM"
    assert result.json()["method"] == "nearest-neighbour + 2-opt on OSRM road-network distances"
    assert result.json()["optimized"]["distance_km"] == 2.0
    assert calls[0][0].startswith("https://osrm.example.test/table/v1/driving/")
    assert calls[0][1]["params"]["annotations"] == "distance,duration"


def test_plan_returns_service_unavailable_when_osrm_fails(client, monkeypatch):
    from app.core.config import get_settings
    from app.services import routing

    def fail_get(*args, **kwargs):
        raise routing.httpx.ConnectError("unavailable")

    monkeypatch.setattr(get_settings(), "osrm_base_url", "https://osrm.example.test")
    monkeypatch.setattr(routing.httpx, "get", fail_get)
    result = client.post("/api/v1/routes/plan", headers=owner(client), json={"stops": STOPS})
    assert result.status_code == 503
    assert "OSRM route matrix request failed" in result.json()["detail"]


def test_fleet_plan_respects_vehicle_capacity_time_windows_and_shifts(client):
    h = owner(client)
    vehicle_ids = [
        client.post(
            "/api/v1/vehicles",
            json={**V, "registration": f"CAP-{i}", "capacity_kg": 10},
            headers=h,
        ).json()["id"]
        for i in range(2)
    ]
    stops = [
        {"address": f"Stop {i}", "lat": 9.01 + i * 0.01, "lng": 38.71, "demand_kg": 7,
         "window_start_minute": 60, "window_end_minute": 100, "service_minutes": 5}
        for i in range(2)
    ]
    vehicles = [
        {"vehicle_id": vehicle_id, "start_lat": 9.0, "start_lng": 38.7,
         "shift_start_minute": 60, "shift_end_minute": 100}
        for vehicle_id in vehicle_ids
    ]
    result = client.post("/api/v1/routes/plan-fleet", headers=h, json={"vehicles": vehicles, "stops": stops})
    assert result.status_code == 200, result.text
    plan = result.json()
    assignments = [stop for route in plan["routes"] for stop in route["stop_indices"]]
    assert sorted(assignments) == [0, 1]
    assert all(len(route["stop_indices"]) <= 1 for route in plan["routes"])
    assert all(60 <= minute <= 100 for route in plan["routes"] for minute in route["arrival_minutes"])
    assert plan["routing_provider"] == "estimate"

    impossible = client.post(
        "/api/v1/routes/plan-fleet",
        headers=h,
        json={
            "vehicles": [{**vehicles[0], "shift_start_minute": 100, "shift_end_minute": 120}],
            "stops": [{**stops[0], "window_start_minute": 0, "window_end_minute": 10}],
        },
    )
    assert impossible.status_code == 422


def test_route_create_read_update_delete_and_delivery_link(client):
    h = owner(client)
    vid = client.post("/api/v1/vehicles", json=V, headers=h).json()["id"]
    did = client.post("/api/v1/deliveries", json={"pickup_address": "A", "dest_address": "Far", "dest_lat": 9.1, "dest_lng": 38.9}, headers=h).json()["id"]
    stops = [{**s} for s in STOPS]
    stops[1]["delivery_id"] = did
    r = client.post("/api/v1/routes", json={"name": "Morning", "stops": stops, "vehicle_id": vid}, headers=h)
    assert r.status_code == 201, r.text
    route = r.json()
    assert route["status"] == "planned" and route["stop_count"] == 5 and route["vehicle_label"].startswith("ET-2001")
    assert [s["sequence"] for s in route["stops"]] == [1, 2, 3, 4, 5]
    assert route["optimization_notes"]["assumptions"]["avg_speed_kph"] == 40 and route["optimization_notes"]["estimates"] is True
    rid = route["id"]
    assert client.get(f"/api/v1/routes/{rid}", headers=h).json()["name"] == "Morning"
    assert client.get("/api/v1/routes", headers=h).json()["items"][0]["stop_count"] == 5
    assert client.patch(f"/api/v1/routes/{rid}", json={"status": "in_progress"}, headers=h).json()["status"] == "in_progress"
    assert client.patch(f"/api/v1/routes/{rid}", json={"status": "bogus"}, headers=h).status_code == 422
    assert client.delete(f"/api/v1/routes/{rid}", headers=h).status_code == 204
    assert client.get(f"/api/v1/routes/{rid}", headers=h).status_code == 404
    assert client.get(f"/api/v1/deliveries/{did}", headers=h).status_code == 200  # delivery survives, just unlinked


def test_unoptimized_route_keeps_given_order(client):
    h = owner(client)
    r = client.post("/api/v1/routes", json={"name": "Manual", "stops": STOPS, "optimize": False}, headers=h).json()
    assert [s["address"] for s in r["stops"]] == [s["address"] for s in STOPS]
    assert r["optimization_notes"]["optimized"] is False


def test_routes_isolation_and_cross_org_references(client):
    a, b = owner(client), owner(client, "b@b.com", "Beta")
    vid = client.post("/api/v1/vehicles", json=V, headers=a).json()["id"]
    did = client.post("/api/v1/deliveries", json={"pickup_address": "A", "dest_address": "B"}, headers=a).json()["id"]
    rid = client.post("/api/v1/routes", json={"name": "R", "stops": STOPS}, headers=a).json()["id"]
    assert client.get(f"/api/v1/routes/{rid}", headers=b).status_code == 404
    assert client.delete(f"/api/v1/routes/{rid}", headers=b).status_code == 404
    assert client.patch(f"/api/v1/routes/{rid}", json={"name": "x"}, headers=b).status_code == 404
    assert client.get("/api/v1/routes", headers=b).json()["total"] == 0
    assert client.post("/api/v1/routes", json={"name": "R", "stops": STOPS, "vehicle_id": vid}, headers=b).status_code == 422
    bad = [{**STOPS[0], "delivery_id": did}, STOPS[1]]
    assert client.post("/api/v1/routes", json={"name": "R", "stops": bad}, headers=b).status_code == 422
    assert client.post("/api/v1/routes/plan", json={"stops": bad}, headers=b).status_code == 422


def test_route_permissions(client):
    o = register(client)["access_token"]
    viewer = invite_and_login(client, o, "v@a.com", "viewer")
    disp = invite_and_login(client, o, "d@a.com", "dispatcher")
    assert client.post("/api/v1/routes", json={"name": "R", "stops": STOPS}, headers=auth(viewer)).status_code == 403
    assert client.post("/api/v1/routes/plan", json={"stops": STOPS}, headers=auth(viewer)).status_code == 200
    assert client.post("/api/v1/routes", json={"name": "R", "stops": STOPS}, headers=auth(disp)).status_code == 201
    assert client.get("/api/v1/routes").status_code == 401


# ------------------------------------------------------- tracking (simulated)
def test_simulation_tick_moves_active_vehicles_and_raises_geofence_events(client):
    h = owner(client)
    client.post("/api/v1/vehicles", json=V, headers=h)
    client.post("/api/v1/vehicles", json={**V, "registration": "ET-2002", "status": "idle"}, headers=h)
    client.post("/api/v1/vehicles", json={**V, "registration": "ET-2003", "status": "retired"}, headers=h)

    from app.core.database import get_session_factory
    from app.main import app
    from app.models import Notification, Organization
    factory = app.dependency_overrides[get_session_factory]()
    with factory() as db:
        org_id = db.query(Organization).first().id
    state = OrgState(rng=random.Random(3))
    with factory() as db:
        placed, events = run_tick(db, org_id, state, advance=False, dt=2, boost=8)
    assert {p["registration"] for p in placed} == {"ET-2001", "ET-2002"}  # retired vehicles are excluded
    assert all(p["simulated"] is True for p in placed) and events == []
    before = {p["registration"]: (p["lat"], p["lng"]) for p in placed}

    # A zone around the active vehicle's start. The first sighting is silent (boost=0: no movement).
    here = before["ET-2001"]
    assert client.post("/api/v1/geofences", json={"name": "Start zone", "center_lat": here[0], "center_lng": here[1], "radius_m": 1000}, headers=h).status_code == 201
    with factory() as db:
        _, first = run_tick(db, org_id, state, advance=True, dt=2, boost=0)
    assert first == []
    seen = []
    for _ in range(40):  # ~4 km per step: the vehicle must leave a 1 km zone
        with factory() as db:
            positions, ev = run_tick(db, org_id, state, advance=True, dt=2, boost=200)
        seen += ev
    assert any(e["event"] == "exit" and e["registration"] == "ET-2001" and e["geofence"] == "Start zone" and e["simulated"] for e in seen)
    after = {p["registration"]: (p["lat"], p["lng"]) for p in positions}
    assert after["ET-2001"] != before["ET-2001"]  # active vehicle moved
    assert after["ET-2002"] == before["ET-2002"]  # idle vehicle stayed put
    stored = client.get("/api/v1/tracking/events", headers=h).json()
    assert stored and stored[0]["geofence"] == "Start zone" and stored[0]["simulated"] is True
    with factory() as db:
        assert db.query(Notification).filter(Notification.organization_id == org_id).count() >= 1
    snap = client.get("/api/v1/tracking/vehicles", headers=h).json()
    assert {p["registration"] for p in snap} == {"ET-2001", "ET-2002"}
    vid = client.get("/api/v1/vehicles?q=2001", headers=h).json()["items"][0]["id"]
    hist = client.get(f"/api/v1/tracking/vehicles/{vid}/history", headers=h).json()
    assert len(hist) >= 1 and all(p["simulated"] for p in hist)


def test_simulation_does_not_overwrite_real_gps_positions(client):
    h = owner(client)
    vehicle_id = client.post("/api/v1/vehicles", json=V, headers=h).json()["id"]

    from datetime import datetime, timezone
    from app.core.database import get_session_factory
    from app.main import app
    from app.models import Organization, Vehicle, VehicleLocation

    factory = app.dependency_overrides[get_session_factory]()
    with factory() as db:
        vehicle = db.get(Vehicle, uuid.UUID(vehicle_id))
        org_id = db.query(Organization).first().id
        vehicle.last_lat, vehicle.last_lng = 8.95, 38.90
        db.add(VehicleLocation(
            organization_id=org_id,
            vehicle_id=vehicle.id,
            lat=9.02,
            lng=38.73,
            speed_kph=32.5,
            heading=180,
            is_simulated=False,
            recorded_at=datetime.now(timezone.utc),
        ))
        db.commit()

    state = OrgState(rng=random.Random(3))
    with factory() as db:
        positions, _ = run_tick(db, org_id, state, advance=True, dt=2, boost=200)

    assert len(positions) == 1
    assert positions[0]["simulated"] is False
    assert (positions[0]["lat"], positions[0]["lng"]) == (9.02, 38.73)
    assert positions[0]["speed_kph"] == 32.5
    assert not state.movers
    with factory() as db:
        vehicle = db.get(Vehicle, uuid.UUID(vehicle_id))
        assert (vehicle.last_lat, vehicle.last_lng) == (9.02, 38.73)
        assert db.query(VehicleLocation).filter(VehicleLocation.is_simulated.is_(True)).count() == 0


def test_tracking_isolation(client):
    a, b = owner(client), owner(client, "b@b.com", "Beta")
    vid = client.post("/api/v1/vehicles", json=V, headers=a).json()["id"]
    assert client.get(f"/api/v1/tracking/vehicles/{vid}/history", headers=b).status_code == 404
    assert client.get("/api/v1/tracking/vehicles", headers=b).json() == []
    assert client.get("/api/v1/tracking/events", headers=b).json() == []
    assert client.get("/api/v1/tracking/vehicles").status_code == 401


def test_websocket_requires_auth_and_sends_only_own_org(client, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "sim_tick_seconds", 60.0)  # no tick during the test, only the snapshot
    ta = register(client)["access_token"]
    tb = register(client, "b@b.com", "Beta")["access_token"]
    client.post("/api/v1/vehicles", json=V, headers=auth(ta))

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/v1/ws/tracking") as ws:
            ws.send_json({"type": "auth", "token": "garbage"})
            ws.receive_json()
    with client.websocket_connect("/api/v1/ws/tracking") as ws:
        ws.send_json({"type": "auth", "token": ta})
        msg = ws.receive_json()
    assert msg["type"] == "snapshot" and msg["simulated"] is True
    assert [v["registration"] for v in msg["vehicles"]] == ["ET-2001"] and msg["vehicles"][0]["simulated"] is True
    with client.websocket_connect("/api/v1/ws/tracking") as ws:
        ws.send_json({"type": "auth", "token": tb})
        assert ws.receive_json()["vehicles"] == []  # another organization sees nothing of Acme's fleet
