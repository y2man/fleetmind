from datetime import date, datetime, timedelta, timezone

from tests.conftest import auth, invite_and_login, register

V = {"registration": "ET-1001", "manufacturer": "Isuzu", "model": "NPR", "year": 2021, "fuel_type": "diesel", "status": "active", "mileage_km": 1200}
D = {"full_name": "Hana Tesfaye", "license_number": "LIC-1", "license_expiry": "2030-01-01"}


def owner(client, email="owner@a.com", org="Acme"):
    return auth(register(client, email, org)["access_token"])


def test_vehicle_crud(client):
    h = owner(client)
    r = client.post("/api/v1/vehicles", json=V, headers=h)
    assert r.status_code == 201, r.text
    vid = r.json()["id"]
    assert client.get(f"/api/v1/vehicles/{vid}", headers=h).json()["registration"] == "ET-1001"
    r = client.patch(f"/api/v1/vehicles/{vid}", json={"status": "maintenance", "mileage_km": 1500}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "maintenance" and r.json()["mileage_km"] == 1500
    assert client.delete(f"/api/v1/vehicles/{vid}", headers=h).status_code == 204
    assert client.get(f"/api/v1/vehicles/{vid}", headers=h).status_code == 404


def test_validation(client):
    h = owner(client)
    assert client.post("/api/v1/vehicles", json={**V, "status": "flying"}, headers=h).status_code == 422
    assert client.post("/api/v1/vehicles", json={**V, "mileage_km": -5}, headers=h).status_code == 422
    assert client.post("/api/v1/vehicles", json={"manufacturer": "x"}, headers=h).status_code == 422
    vid = client.post("/api/v1/vehicles", json=V, headers=h).json()["id"]
    assert client.patch(f"/api/v1/vehicles/{vid}", json={"registration": None}, headers=h).status_code == 422
    assert client.post("/api/v1/fuel", json={"vehicle_id": vid, "liters": 0, "cost": 5}, headers=h).status_code == 422


def test_unique_registration_conflict(client):
    h = owner(client)
    assert client.post("/api/v1/vehicles", json=V, headers=h).status_code == 201
    assert client.post("/api/v1/vehicles", json=V, headers=h).status_code == 409


def test_same_registration_allowed_in_other_org(client):
    a, b = owner(client), owner(client, "b@b.com", "Beta")
    assert client.post("/api/v1/vehicles", json=V, headers=a).status_code == 201
    assert client.post("/api/v1/vehicles", json=V, headers=b).status_code == 201


def test_organization_isolation(client):
    a, b = owner(client), owner(client, "b@b.com", "Beta")
    vid = client.post("/api/v1/vehicles", json=V, headers=a).json()["id"]
    did = client.post("/api/v1/drivers", json=D, headers=a).json()["id"]
    assert client.get("/api/v1/vehicles", headers=b).json()["total"] == 0
    assert client.get("/api/v1/vehicles/options", headers=b).json() == []
    for path in (f"/api/v1/vehicles/{vid}", f"/api/v1/drivers/{did}"):
        assert client.get(path, headers=b).status_code == 404
        assert client.patch(path, json={"status": "idle"} if "vehicles" in path else {"full_name": "X"}, headers=b).status_code == 404
        assert client.delete(path, headers=b).status_code == 404
    assert client.get(f"/api/v1/vehicles/{vid}", headers=a).status_code == 200  # untouched


def test_cannot_reference_other_orgs_records(client):
    a, b = owner(client), owner(client, "b@b.com", "Beta")
    vid = client.post("/api/v1/vehicles", json=V, headers=a).json()["id"]
    did = client.post("/api/v1/drivers", json=D, headers=a).json()["id"]
    body = {"pickup_address": "A", "dest_address": "B"}
    assert client.post("/api/v1/deliveries", json={**body, "vehicle_id": vid}, headers=b).status_code == 422
    assert client.post("/api/v1/deliveries", json={**body, "driver_id": did}, headers=b).status_code == 422
    assert client.post("/api/v1/fuel", json={"vehicle_id": vid, "liters": 10, "cost": 5}, headers=b).status_code == 422
    assert client.post("/api/v1/maintenance", json={"vehicle_id": vid, "description": "x"}, headers=b).status_code == 422


def test_permissions_by_role(client):
    o = register(client)["access_token"]
    viewer = invite_and_login(client, o, "v@a.com", "viewer")
    disp = invite_and_login(client, o, "d@a.com", "dispatcher")
    assert client.get("/api/v1/vehicles", headers=auth(viewer)).status_code == 200
    assert client.post("/api/v1/vehicles", json=V, headers=auth(viewer)).status_code == 403
    assert client.post("/api/v1/vehicles", json=V, headers=auth(disp)).status_code == 403
    r = client.post("/api/v1/deliveries", json={"pickup_address": "A", "dest_address": "B"}, headers=auth(disp))
    assert r.status_code == 201 and r.json()["reference"].startswith("D-")
    assert client.post("/api/v1/deliveries", json={"pickup_address": "A", "dest_address": "B"}, headers=auth(viewer)).status_code == 403
    assert client.delete(f"/api/v1/deliveries/{r.json()['id']}", headers=auth(viewer)).status_code == 403
    assert client.get("/api/v1/vehicles").status_code == 401


def test_list_search_filter_sort_paginate(client):
    h = owner(client)
    for i, (m, st) in enumerate([("Isuzu", "active"), ("Toyota", "idle"), ("Isuzu", "idle"), ("Volvo", "active"), ("Ford", "retired")]):
        assert client.post("/api/v1/vehicles", json={**V, "registration": f"R-{i}", "manufacturer": m, "status": st}, headers=h).status_code == 201
    j = client.get("/api/v1/vehicles?page_size=2&page=2&sort=registration&order=asc", headers=h).json()
    assert j["total"] == 5 and [x["registration"] for x in j["items"]] == ["R-2", "R-3"]
    assert client.get("/api/v1/vehicles?status=idle", headers=h).json()["total"] == 2
    assert client.get("/api/v1/vehicles?q=isu", headers=h).json()["total"] == 2
    assert client.get("/api/v1/vehicles?q=%25", headers=h).json()["total"] == 0  # wildcard is escaped
    assert client.get("/api/v1/vehicles?page_size=1000", headers=h).status_code == 422
    assert client.get("/api/v1/vehicles?sort=password_hash", headers=h).status_code == 200  # unknown sort is ignored
    assert client.get("/api/v1/vehicles?driver_id=not-a-uuid", headers=h).status_code == 422


def test_labels_and_delivery_status_times(client):
    h = owner(client)
    vid = client.post("/api/v1/vehicles", json=V, headers=h).json()["id"]
    did = client.post("/api/v1/drivers", json=D, headers=h).json()["id"]
    r = client.post("/api/v1/deliveries", json={"pickup_address": "A", "dest_address": "B", "vehicle_id": vid, "driver_id": did}, headers=h).json()
    assert r["vehicle_label"].startswith("ET-1001") and r["driver_label"] == "Hana Tesfaye"
    done = client.patch(f"/api/v1/deliveries/{r['id']}", json={"status": "delivered"}, headers=h).json()
    assert done["delivered_at"] is not None
    back = client.patch(f"/api/v1/deliveries/{r['id']}", json={"status": "in_transit"}, headers=h).json()
    assert back["delivered_at"] is None
    assert client.get(f"/api/v1/deliveries?vehicle_id={vid}", headers=h).json()["total"] == 1


def test_deleting_driver_unassigns_vehicle(client):
    h = owner(client)
    did = client.post("/api/v1/drivers", json=D, headers=h).json()["id"]
    vid = client.post("/api/v1/vehicles", json={**V, "driver_id": did}, headers=h).json()["id"]
    assert client.delete(f"/api/v1/drivers/{did}", headers=h).status_code == 204
    assert client.get(f"/api/v1/vehicles/{vid}", headers=h).json()["driver_id"] is None


def test_fuel_and_maintenance(client):
    h = owner(client)
    vid = client.post("/api/v1/vehicles", json=V, headers=h).json()["id"]
    f = client.post("/api/v1/fuel", json={"vehicle_id": vid, "liters": 40.5, "cost": 62.25, "station": "Total"}, headers=h)
    assert f.status_code == 201 and f.json()["cost"] == 62.25 and f.json()["occurred_at"]
    m = client.post("/api/v1/maintenance", json={"vehicle_id": vid, "description": "Oil change", "scheduled_for": "2030-01-01"}, headers=h)
    assert m.status_code == 201
    done = client.patch(f"/api/v1/maintenance/{m.json()['id']}", json={"status": "completed"}, headers=h).json()
    assert done["completed_at"] is not None
    assert client.delete(f"/api/v1/vehicles/{vid}", headers=h).status_code == 204  # cascades
    assert client.get("/api/v1/fuel", headers=h).json()["total"] == 0


def test_audit_log_records_changes(client):
    h = owner(client)
    vid = client.post("/api/v1/vehicles", json=V, headers=h).json()["id"]
    client.patch(f"/api/v1/vehicles/{vid}", json={"status": "idle"}, headers=h)
    client.delete(f"/api/v1/vehicles/{vid}", headers=h)
    actions = [a["action"] for a in client.get("/api/v1/audit-logs?limit=50", headers=h).json()]
    assert {"vehicle.created", "vehicle.updated", "vehicle.deleted"} <= set(actions)


def test_dashboard_empty_and_real_numbers(client):
    h = owner(client)
    d = client.get("/api/v1/dashboard?days=30", headers=h).json()
    assert d["has_data"] is False and len(d["deliveries"]) == 10
    k = {x["key"]: x["value"] for x in d["kpis"]}
    assert k["vehicles"] == 0 and k["utilization"] is None and k["success"] is None

    past = (date.today() - timedelta(days=5)).isoformat()
    client.post("/api/v1/vehicles", json={**V, "insurance_expiry": past}, headers=h)
    client.post("/api/v1/vehicles", json={**V, "registration": "ET-2", "status": "idle"}, headers=h)
    vid = client.get("/api/v1/vehicles?q=ET-2", headers=h).json()["items"][0]["id"]
    now = datetime.now(timezone.utc)
    client.post("/api/v1/deliveries", json={"pickup_address": "A", "dest_address": "B", "status": "delivered"}, headers=h)
    client.post("/api/v1/deliveries", json={"pickup_address": "A", "dest_address": "B", "status": "in_transit"}, headers=h)
    client.post("/api/v1/deliveries", json={"pickup_address": "A", "dest_address": "B", "status": "assigned", "deadline": (now - timedelta(hours=2)).isoformat()}, headers=h)
    client.post("/api/v1/fuel", json={"vehicle_id": vid, "liters": 30, "cost": 45.5}, headers=h)
    client.post("/api/v1/maintenance", json={"vehicle_id": vid, "description": "Brakes", "scheduled_for": past}, headers=h)

    for days, n in ((7, 7), (30, 10), (90, 9)):
        assert len(client.get(f"/api/v1/dashboard?days={days}", headers=h).json()["fuel"]) == n
    d = client.get("/api/v1/dashboard?days=30", headers=h).json()
    k = {x["key"]: x["value"] for x in d["kpis"]}
    assert d["has_data"] and k["vehicles"] == 2 and k["active"] == 1 and k["available"] == 1
    assert k["completed"] == 1 and k["delayed"] == 1 and k["active_deliveries"] == 2
    assert k["fuel"] == 45.5 and k["utilization"] == 50.0 and k["success"] == 50.0
    assert sum(p["cost"] for p in d["fuel"]) == 45.5
    texts = " ".join(a["text"] for a in d["alerts"])
    assert "insurance expired" in texts and "maintenance overdue" in texts and d["alerts"][0]["severity"] == "critical"
    assert d["maintenance"][0]["overdue"] is True and d["activity"]


def test_dashboard_is_org_scoped(client):
    a, b = owner(client), owner(client, "b@b.com", "Beta")
    client.post("/api/v1/vehicles", json=V, headers=a)
    k = {x["key"]: x["value"] for x in client.get("/api/v1/dashboard", headers=b).json()["kpis"]}
    assert k["vehicles"] == 0
    assert client.get("/api/v1/dashboard").status_code == 401
