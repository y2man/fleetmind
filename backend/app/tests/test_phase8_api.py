"""Phase 8 API tests: analytics, exports, notifications (smart alerts) and global search."""
from datetime import date, datetime, timedelta, timezone

from tests.conftest import auth, invite_and_login, register

NOW = datetime.now(timezone.utc)
iso = lambda dt: dt.isoformat()  # noqa: E731
A = "/api/v1/analytics"


def owner(client, email="owner@a.com", org="Acme"):
    return auth(register(client, email, org)["access_token"])


def vehicle(client, h, reg="ET-3001", **extra):
    r = client.post("/api/v1/vehicles", json={"registration": reg, "manufacturer": "Isuzu", "model": "NPR", "status": "active", **extra}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def delivery(client, h, **kw):
    r = client.post("/api/v1/deliveries", json={"pickup_address": "Depot", "dest_address": "Customer", **kw}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def kpis(client, h, query="?days=30"):
    r = client.get(f"{A}{query}", headers=h)
    assert r.status_code == 200, r.text
    return {k["key"]: k for k in r.json()["kpis"]}, r.json()


# ---------------------------------------------------------------- analytics
def test_analytics_requires_login(client):
    assert client.get(A).status_code == 401
    assert client.get("/api/v1/notifications").status_code == 401
    assert client.get("/api/v1/search?q=ab").status_code == 401


def test_analytics_empty_org(client):
    h = owner(client)
    k, body = kpis(client, h)
    assert not body["has_data"] and k["delivered"]["value"] == 0 and k["on_time_rate"]["value"] is None
    assert body["range"]["days"] == 30 and body["range"]["bucket_days"] == 1 and len(body["series"]) == 30


def test_analytics_real_numbers_and_org_isolation(client):
    h, other = owner(client), owner(client, "b@b.com", "Beta")
    vid = vehicle(client, h)
    delivery(client, h, status="delivered", deadline=iso(NOW + timedelta(days=1)))            # on time
    delivery(client, h, status="delivered", deadline=iso(NOW - timedelta(days=1)))            # delivered after its deadline
    delivery(client, h, status="in_transit", deadline=iso(NOW - timedelta(hours=3)))          # open past deadline
    client.post("/api/v1/fuel", json={"vehicle_id": vid, "liters": 40, "cost": 100, "occurred_at": iso(NOW - timedelta(days=2))}, headers=h)
    k, body = kpis(client, h)
    assert k["created"]["value"] == 3 and k["delivered"]["value"] == 2
    assert k["on_time_rate"]["value"] == 50.0 and k["late"]["value"] == 2
    assert k["fuel_cost"]["value"] == 100.0 and k["liters"]["value"] == 40.0
    assert body["fuel_by_vehicle"][0]["vehicle"] == "ET-3001"
    ko, bo = kpis(client, other)  # the other organization sees none of it
    assert ko["created"]["value"] == 0 and ko["fuel_cost"]["value"] == 0 and bo["fuel_by_vehicle"] == []


def test_analytics_custom_range_and_validation(client):
    h = owner(client)
    today = datetime.now(timezone.utc).date()
    ok = client.get(f"{A}?start={today - timedelta(days=6)}&end={today}", headers=h)
    assert ok.status_code == 200 and ok.json()["range"]["days"] == 7
    assert client.get(f"{A}?start={today}&end={today - timedelta(days=1)}", headers=h).status_code == 422       # start after end
    assert client.get(f"{A}?start={today}", headers=h).status_code == 422                                          # only one date
    assert client.get(f"{A}?start={today}&end={today + timedelta(days=2)}", headers=h).status_code == 422        # future
    assert client.get(f"{A}?start={today - timedelta(days=400)}&end={today}", headers=h).status_code == 422      # too long
    assert client.get(f"{A}?days=0", headers=h).status_code == 422
    assert client.get(f"{A}?days=9999", headers=h).status_code == 422
    assert client.get(f"{A}?start=not-a-date&end={today}", headers=h).status_code == 422


# ----------------------------------------------------------------- exports
def test_csv_export_content_headers_and_audit(client):
    h = owner(client)
    vid = vehicle(client, h)
    client.post("/api/v1/fuel", json={"vehicle_id": vid, "liters": 30, "cost": 50, "station": "=HYPERLINK(\"http://evil\")", "occurred_at": iso(NOW - timedelta(days=1))}, headers=h)
    r = client.get(f"{A}/export/fuel?days=30", headers=h)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"] and r.headers["content-disposition"].endswith('.csv"')
    assert r.headers["cache-control"] == "no-store"
    text = r.content.decode("utf-8-sig")
    assert text.splitlines()[0].startswith("Date,Vehicle")
    assert "ET-3001" in text and "'=HYPERLINK" in text and ",=HYPERLINK" not in text  # formula neutralised
    logs = client.get("/api/v1/audit-logs?limit=50", headers=h).json()
    assert any(a["action"] == "export.csv" for a in logs)


def test_csv_all_datasets_and_unknown(client):
    h = owner(client)
    vehicle(client, h)
    for name in ("vehicles", "drivers", "deliveries", "fuel", "maintenance"):
        r = client.get(f"{A}/export/{name}?days=90", headers=h)
        assert r.status_code == 200, (name, r.text)
        assert len(r.content.decode("utf-8-sig").splitlines()) >= 1
    assert client.get(f"{A}/export/users", headers=h).status_code == 404
    assert client.get(f"{A}/export/vehicles?days=0", headers=h).status_code == 422


def test_csv_export_is_org_scoped(client):
    a, b = owner(client), owner(client, "b@b.com", "Beta")
    vehicle(client, a, "ET-SECRET")
    assert "ET-SECRET" not in client.get(f"{A}/export/vehicles", headers=b).content.decode("utf-8-sig")


def test_pdf_report(client):
    h = owner(client)
    vehicle(client, h)
    r = client.get(f"{A}/report?days=30", headers=h)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF") and b"%%EOF" in r.content[-20:]
    assert "attachment" in r.headers["content-disposition"]
    assert any(a["action"] == "export.pdf" for a in client.get("/api/v1/audit-logs?limit=50", headers=h).json())
    assert client.get(f"{A}/report?days=0", headers=h).status_code == 422


def test_viewer_can_read_analytics_and_export_what_they_can_read(client):
    h = owner(client)
    vehicle(client, h)
    viewer = auth(invite_and_login(client, h["Authorization"].split()[1], "v@a.com", "viewer"))
    assert client.get(A, headers=viewer).status_code == 200
    assert client.get(f"{A}/export/vehicles", headers=viewer).status_code == 200
    assert client.get(f"{A}/report", headers=viewer).status_code == 200


# ----------------------------------------------------------- notifications
def test_refresh_raises_alerts_once_and_counts_unread(client):
    h = owner(client)
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    vehicle(client, h, insurance_expiry=yesterday)
    r = client.post("/api/v1/notifications/refresh", headers=h)
    assert r.status_code == 200 and r.json()["created"] >= 1 and r.json()["unread_count"] >= 1
    again = client.post("/api/v1/notifications/refresh", headers=h).json()
    assert again["created"] == 0 and again["unread_count"] == r.json()["unread_count"]  # same condition is not raised twice
    items = client.get("/api/v1/notifications", headers=h).json()["items"]
    assert any(n["severity"] == "critical" and "insurance" in n["title"] and n["link"] == "/app/fleet" for n in items)
    assert all(n["is_read"] is False for n in items)


def test_mark_read_is_per_user_and_stays_read_after_refresh(client):
    h = owner(client)
    token = h["Authorization"].split()[1]
    vehicle(client, h, insurance_expiry=(datetime.now(timezone.utc).date() - timedelta(days=2)).isoformat())
    client.post("/api/v1/notifications/refresh", headers=h)
    colleague = auth(invite_and_login(client, token, "d@a.com", "dispatcher"))
    first = client.get("/api/v1/notifications", headers=h).json()
    nid = first["items"][0]["id"]
    total = first["unread_count"]
    r = client.post(f"/api/v1/notifications/{nid}/read", headers=h)
    assert r.status_code == 200 and r.json()["unread_count"] == total - 1
    assert client.post(f"/api/v1/notifications/{nid}/read", headers=h).status_code == 200   # idempotent
    mine = client.get("/api/v1/notifications", headers=h).json()
    theirs = client.get("/api/v1/notifications", headers=colleague).json()
    assert mine["unread_count"] == total - 1 and theirs["unread_count"] == total          # a colleague still sees it unread
    assert next(n for n in mine["items"] if n["id"] == nid)["is_read"] is True
    client.post("/api/v1/notifications/refresh", headers=h)
    assert client.get("/api/v1/notifications", headers=h).json()["unread_count"] == total - 1  # refresh does not resurrect it
    only = client.get("/api/v1/notifications?unread_only=true", headers=h).json()["items"]
    assert nid not in [n["id"] for n in only]
    done = client.post("/api/v1/notifications/read-all", headers=h).json()
    assert done["unread_count"] == 0 and client.get("/api/v1/notifications", headers=colleague).json()["unread_count"] == total


def test_notifications_are_org_scoped(client):
    a, b = owner(client), owner(client, "b@b.com", "Beta")
    vehicle(client, a, insurance_expiry=(datetime.now(timezone.utc).date() - timedelta(days=2)).isoformat())
    client.post("/api/v1/notifications/refresh", headers=a)
    nid = client.get("/api/v1/notifications", headers=a).json()["items"][0]["id"]
    assert client.get("/api/v1/notifications", headers=b).json() == {"items": [], "unread_count": 0}
    assert client.post(f"/api/v1/notifications/{nid}/read", headers=b).status_code == 404
    assert client.get("/api/v1/notifications", headers=a).json()["unread_count"] >= 1


def test_late_delivery_alert(client):
    h = owner(client)
    delivery(client, h, status="in_transit", deadline=iso(NOW - timedelta(hours=4)))
    created = client.post("/api/v1/notifications/refresh", headers=h).json()["created"]
    assert created >= 1
    titles = [n["title"] for n in client.get("/api/v1/notifications", headers=h).json()["items"]]
    assert any("is late" in t for t in titles)


# -------------------------------------------------------------------- search
def test_search_finds_records_and_is_org_scoped(client):
    a, b = owner(client), owner(client, "b@b.com", "Beta")
    vehicle(client, a, "ET-7777")
    client.post("/api/v1/drivers", json={"full_name": "Selam Bekele", "license_number": "LIC-77"}, headers=a)
    delivery(client, a, reference="D-SEARCH-1", dest_address="Bole Road")
    r = client.get("/api/v1/search?q=7777", headers=a).json()
    assert r["results"][0]["type"] == "vehicle" and r["results"][0]["title"] == "ET-7777" and r["results"][0]["url"].startswith("/app/fleet?q=")
    assert [x["type"] for x in client.get("/api/v1/search?q=selam", headers=a).json()["results"]] == ["driver"]
    assert [x["title"] for x in client.get("/api/v1/search?q=bole", headers=a).json()["results"]] == ["D-SEARCH-1"]
    assert client.get("/api/v1/search?q=7777", headers=b).json()["results"] == []


def test_search_validation_and_wildcards(client):
    h = owner(client)
    vehicle(client, h, "ET-1111")
    assert client.get("/api/v1/search?q=a", headers=h).status_code == 422
    assert client.get("/api/v1/search?q=" + "x" * 101, headers=h).status_code == 422
    assert client.get("/api/v1/search?q=%25%25", headers=h).json()["results"] == []   # "%%" is literal text, not "match everything"
    assert client.get("/api/v1/search?q=__", headers=h).json()["results"] == []
    assert client.get("/api/v1/search?q=%20%20", headers=h).json()["results"] == []   # whitespace only
