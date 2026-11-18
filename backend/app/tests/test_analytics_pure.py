"""Pure unit tests (no database, no HTTP): analytics math, smart alert rules, CSV safety, PDF output."""
import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace as NS

from app.services import alerts, analytics, exports
from app.services.insights import OrgData
from app.services.pdf import Pdf, fit, text_width

NOW = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
TODAY = NOW.date()


def veh(reg="ET-1", **kw):
    base = dict(id=uuid.uuid4(), registration=reg, manufacturer="Isuzu", model="NPR", year=2020, fuel_type="diesel", status="active", mileage_km=1000,
                capacity_kg=None, driver_id=None, insurance_expiry=None, registration_expiry=None)
    return NS(**{**base, **kw})


def drv(name="Hana", **kw):
    base = dict(id=uuid.uuid4(), full_name=name, email=None, phone=None, license_number="L-" + name, license_expiry=None, availability="available", safety_score=None)
    return NS(**{**base, **kw})


def dlv(ref="D-1", **kw):
    base = dict(id=uuid.uuid4(), reference=ref, status="pending", pickup_address="A", dest_address="B", weight_kg=None, deadline=None, delivered_at=None,
                created_at=NOW - timedelta(days=2), vehicle_id=None, driver_id=None, pickup_lat=None, pickup_lng=None, dest_lat=None, dest_lng=None)
    return NS(**{**base, **kw})


def fuel(v, liters=40.0, cost=60.0, days_ago=1, **kw):
    base = dict(id=uuid.uuid4(), vehicle_id=v.id, driver_id=None, liters=liters, cost=cost, odometer_km=None, station="S", occurred_at=NOW - timedelta(days=days_ago))
    return NS(**{**base, **kw})


def maint(v, **kw):
    base = dict(id=uuid.uuid4(), vehicle_id=v.id, kind="preventive", description="Oil change", status="scheduled", cost=None, odometer_km=None,
                scheduled_for=None, completed_at=None, created_at=NOW - timedelta(days=10))
    return NS(**{**base, **kw})


# ------------------------------------------------------------- analytics
def test_bucket_sizes():
    assert [analytics.bucket_days(n) for n in (1, 31, 32, 180, 181, 366)] == [1, 1, 7, 7, 30, 30]


def test_compute_counts_and_on_time_rate():
    v, d = veh(), drv()
    deliveries = [
        dlv("D-1", status="delivered", driver_id=d.id, deadline=NOW - timedelta(days=3), delivered_at=NOW - timedelta(days=4), created_at=NOW - timedelta(days=6)),   # on time
        dlv("D-2", status="delivered", driver_id=d.id, deadline=NOW - timedelta(days=3), delivered_at=NOW - timedelta(days=2), created_at=NOW - timedelta(days=6)),   # late
        dlv("D-3", status="delivered", driver_id=d.id, delivered_at=NOW - timedelta(days=1), created_at=NOW - timedelta(days=5)),                                   # no deadline
        dlv("D-4", status="in_transit", deadline=NOW - timedelta(hours=5), created_at=NOW - timedelta(days=1)),                                                      # open and past deadline
        dlv("D-5", status="delivered", driver_id=d.id, deadline=NOW - timedelta(days=60), delivered_at=NOW - timedelta(days=61), created_at=NOW - timedelta(days=70)),  # outside range
    ]
    data = OrgData([v], [d], deliveries, [fuel(v, 50, 100, 1), fuel(v, 30, 45, 3), fuel(v, 10, 20, 40)], [maint(v, status="completed", cost=200, completed_at=NOW - timedelta(days=2))])
    r = analytics.compute(data, TODAY - timedelta(days=13), TODAY, NOW)
    k = {x["key"]: x for x in r["kpis"]}
    assert r["range"]["days"] == 14 and r["range"]["bucket_days"] == 1 and len(r["series"]) == 14
    assert k["delivered"]["value"] == 3 and k["created"]["value"] == 4
    assert k["on_time_rate"]["value"] == 50.0  # 1 of 2 with a deadline
    assert k["late"]["value"] == 2  # D-2 delivered late, D-4 open past deadline
    assert k["fuel_cost"]["value"] == 145.0 and k["liters"]["value"] == 80.0 and k["cost_per_liter"]["value"] == round(145 / 80, 3)
    assert k["maint_cost"]["value"] == 200.0
    assert sum(p["delivered"] for p in r["series"]) == 3 and sum(p["fuel_cost"] for p in r["series"]) == 145.0
    assert r["fuel_by_vehicle"][0]["vehicle"] == "ET-1" and r["fuel_by_vehicle"][0]["fills"] == 2
    assert r["drivers"][0]["driver"] == "Hana" and r["drivers"][0]["delivered"] == 3 and r["drivers"][0]["on_time_rate_pct"] == 50.0
    assert {x["status"]: x["count"] for x in r["delivery_status"]} == {"delivered": 3, "in_transit": 1}
    assert any("no deadline" in n for n in r["notes"])
    assert r["has_data"]


def test_previous_period_comparison_and_blank_change():
    v = veh()
    data = OrgData([v], [], [], [fuel(v, 10, 100, 1), fuel(v, 10, 50, 8)], [])
    r = analytics.compute(data, TODAY - timedelta(days=6), TODAY, NOW)  # 7 days; previous is days 8-14 ago
    k = {x["key"]: x for x in r["kpis"]}
    assert k["fuel_cost"]["value"] == 100.0 and k["fuel_cost"]["previous"] == 50.0 and k["fuel_cost"]["change_pct"] == 100.0
    assert k["delivered"]["change_pct"] is None  # previous is 0: no percent
    assert k["on_time_rate"]["value"] is None


def test_empty_org_is_all_zero_not_error():
    r = analytics.compute(OrgData(), TODAY - timedelta(days=29), TODAY, NOW)
    assert not r["has_data"] and r["delivery_status"] == [] and r["fuel_by_vehicle"] == []
    assert all(p["created"] == 0 and p["fuel_cost"] == 0 for p in r["series"])
    assert any("no activity" in n.lower() for n in r["notes"])


def test_single_day_and_year_range_bucket_edges():
    one = analytics.compute(OrgData(), TODAY, TODAY, NOW)
    assert len(one["series"]) == 1
    yr = analytics.compute(OrgData(), TODAY - timedelta(days=364), TODAY, NOW)
    assert yr["range"]["bucket_days"] == 30 and len(yr["series"]) == 13


def test_naive_datetimes_are_treated_as_utc():
    v = veh()
    f = fuel(v, 10, 10, 1, occurred_at=(NOW - timedelta(days=1)).replace(tzinfo=None))
    r = analytics.compute(OrgData([v], [], [], [f], []), TODAY - timedelta(days=6), TODAY, NOW)
    assert r["kpis"][4]["value"] == 10.0


# ------------------------------------------------------------- alerts
def test_alerts_rules_and_dedupe_keys():
    v = veh("ET-9", insurance_expiry=TODAY - timedelta(days=3), registration_expiry=TODAY + timedelta(days=10))
    d = drv("Abel", license_expiry=TODAY + timedelta(days=200))
    late = dlv("D-LATE", status="in_transit", deadline=NOW - timedelta(hours=2), vehicle_id=v.id)
    over = maint(v, scheduled_for=TODAY - timedelta(days=4))
    out = alerts.build_alerts(OrgData([v], [d], [late], [], [over]), NOW)
    by_kind = {}
    for a in out:
        by_kind.setdefault(a["kind"], []).append(a)
    assert {a["severity"] for a in by_kind["document_expiry"]} == {"critical", "warning"}
    assert by_kind["maintenance_overdue"][0]["severity"] == "critical" and by_kind["maintenance_overdue"][0]["link"] == "/app/maintenance"
    assert by_kind["delivery_late"][0]["title"] == "Delivery D-LATE is late"
    assert len({a["key"] for a in out}) == len(out) and all(len(a["key"]) <= 160 and len(a["title"]) <= 160 for a in out)
    assert [a["severity"] for a in out] == sorted((a["severity"] for a in out), key=lambda s: {"critical": 0, "warning": 1, "info": 2}[s])
    # Same facts give the same keys (so a condition is raised only once) ...
    assert [a["key"] for a in alerts.build_alerts(OrgData([v], [d], [late], [], [over]), NOW + timedelta(hours=1))] == [a["key"] for a in out]
    # ... and a renewed document gives a different key.
    v2 = veh("ET-9", insurance_expiry=TODAY + timedelta(days=365))
    v2.id = v.id
    assert not any(a["kind"] == "document_expiry" and "insurance" in a["title"] for a in alerts.build_alerts(OrgData([v2], [], [], [], []), NOW))


def test_alerts_quiet_fleet_has_none():
    v = veh(insurance_expiry=TODAY + timedelta(days=300), registration_expiry=TODAY + timedelta(days=300))
    assert alerts.build_alerts(OrgData([v], [drv(license_expiry=TODAY + timedelta(days=300))], [dlv(status="delivered", deadline=NOW + timedelta(days=1))], [], []), NOW) == []


def test_retired_vehicle_documents_are_ignored():
    v = veh(status="retired", insurance_expiry=TODAY - timedelta(days=100))
    assert alerts.build_alerts(OrgData([v], [], [], [], []), NOW) == []


# ------------------------------------------------------------- exports
def test_csv_formula_injection_is_neutralised():
    for s in ("=1+1", "+cmd", "-2+3", "@SUM(A1)", "\tx", "\rx"):
        assert exports.safe_cell(s) == "'" + s
    assert exports.safe_cell("Shell Addis") == "Shell Addis"
    assert exports.safe_cell(-5) == -5 and exports.safe_cell(None) == "" and exports.safe_cell(True) == "yes"
    assert exports.safe_cell(date(2026, 1, 2)) == "2026-01-02"


def test_csv_quotes_commas_and_bom():
    out = exports.to_csv(["a", "b"], [["x,y", 'say "hi"'], ["=evil", 3]])
    assert out.startswith("\ufeff") and out.count("\r\n") == 3
    assert '"x,y"' in out and '"say ""hi"""' in out and "'=evil" in out


def test_dataset_rows_honor_range_and_resolve_names():
    v, d = veh("ET-5"), drv("Sara")
    inside = dlv("D-IN", vehicle_id=v.id, driver_id=d.id, created_at=NOW - timedelta(days=2))
    outside = dlv("D-OUT", created_at=NOW - timedelta(days=90))
    data = OrgData([v], [d], [inside, outside], [fuel(v, days_ago=1), fuel(v, days_ago=100)], [])
    h, rows, filtered = exports.dataset_rows("deliveries", data, TODAY - timedelta(days=10), TODAY)
    assert filtered and [r[0] for r in rows] == ["D-IN"] and rows[0][h.index("Vehicle")] == "ET-5" and rows[0][h.index("Driver")] == "Sara"
    assert len(exports.dataset_rows("fuel", data, TODAY - timedelta(days=10), TODAY)[1]) == 1
    h, rows, filtered = exports.dataset_rows("vehicles", data, TODAY, TODAY)
    assert not filtered and len(rows) == 1
    try:
        exports.dataset_rows("users", data, TODAY, TODAY)
        raise AssertionError("expected KeyError")
    except KeyError:
        pass


def test_pdf_is_valid_and_paginates():
    p = Pdf("T")
    p.title_block("Title", "sub")
    p.table(["A", "B"], [[f"row {i} (x) \\ y", str(i)] for i in range(200)], [3, 1], ["l", "r"])
    p.paragraph("café – “quotes” 日本")  # characters outside cp1252 must not crash
    b = p.render()
    assert b.startswith(b"%PDF-1.4") and b.rstrip().endswith(b"%%EOF") and b.count(b"/Type /Page ") >= 3
    assert b"page 1 of" in b


def test_fit_and_width_helpers():
    assert fit("short", 200, 9) == "short"
    s = fit("x" * 200, 80, 9)
    assert s.endswith("…") and text_width(s, 9) <= 80
    assert text_width("WWW", 10) > text_width("iii", 10)


def test_analytics_pdf_renders_from_report():
    v = veh()
    report = analytics.compute(OrgData([v], [drv()], [dlv(status="delivered", deadline=NOW, delivered_at=NOW - timedelta(hours=1))], [fuel(v)], []), TODAY - timedelta(days=29), TODAY, NOW)
    b = exports.analytics_pdf(report, "Acme (Test)")
    assert b.startswith(b"%PDF") and len(b) > 1500
