"""Phase 9: seeding a real (in-memory SQLite) database and using the seeded organization through the API."""
import pathlib

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.main import app
from app.models import Organization, User, Vehicle
from app.seed.generator import DEMO_ORG_NAME, DEMO_PASSWORD, DEMO_USERS
from app.seed.runner import SeedError, seed
from tests.conftest import auth, register

API = "/api/v1"


@pytest.fixture()
def db(client):  # `client` creates the schema and installs the session factory override
    session = app.dependency_overrides[get_session_factory]()()
    yield session
    session.close()


def login(client, role):
    email = next(u["email"] for u in DEMO_USERS if u["role_name"] == role)
    r = client.post(f"{API}/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert r.status_code == 200, r.text
    return auth(r.json()["access_token"])


def count(db, model, org_name=DEMO_ORG_NAME):
    return db.scalar(select(func.count()).select_from(model).where(model.organization_id == select(Organization.id).where(Organization.name == org_name).scalar_subquery()))


def test_seed_creates_the_demo_organization(db):
    result = seed(db)
    assert result["status"] == "created" and result["counts"]["vehicles"] == 14
    assert count(db, Vehicle) == 14
    assert db.scalar(select(func.count()).select_from(User)) == 4


def test_every_demo_role_can_sign_in(client, db):
    seed(db)
    for role in ("owner", "admin", "dispatcher", "viewer"):
        me = client.get(f"{API}/auth/me", headers=login(client, role))
        assert me.status_code == 200 and me.json()["role"] == role


def test_dashboard_and_analytics_show_real_numbers(client, db):
    seed(db)
    h = login(client, "owner")
    dash = client.get(f"{API}/dashboard?days=30", headers=h).json()
    assert dash["has_data"] and {k["key"]: k["value"] for k in dash["kpis"]}["vehicles"] == 14
    assert sum(dash["vehicle_status"].values()) == 14 and dash["alerts"]
    ana = client.get(f"{API}/analytics?days=90", headers=h)
    assert ana.status_code == 200 and ana.json()["has_data"]


def test_exports_work_on_seeded_data(client, db):
    seed(db)
    h = login(client, "owner")
    r = client.get(f"{API}/analytics/export/deliveries", headers=h)
    assert r.status_code == 200 and len(r.text.splitlines()) > 100


def test_smart_alerts_fire_once(client, db):
    seed(db)
    h = login(client, "owner")
    assert client.post(f"{API}/notifications/refresh", headers=h).json()["created"] >= 5
    assert client.post(f"{API}/notifications/refresh", headers=h).json()["created"] == 0  # each condition is raised once
    items = client.get(f"{API}/notifications?limit=100", headers=h).json()["items"]
    assert any(i["severity"] == "critical" for i in items) and any(i["kind"] == "document_expiry" for i in items)


def test_roles_are_enforced_on_demo_data(client, db):
    seed(db)
    viewer, dispatcher = login(client, "viewer"), login(client, "dispatcher")
    vehicle = {"registration": "ET-ZZ1", "manufacturer": "Isuzu", "model": "NPR"}
    assert client.get(f"{API}/vehicles", headers=viewer).json()["total"] == 14
    assert client.post(f"{API}/vehicles", json=vehicle, headers=viewer).status_code == 403
    assert client.post(f"{API}/vehicles", json=vehicle, headers=dispatcher).status_code == 403
    assert client.post(f"{API}/deliveries", json={"pickup_address": "A", "dest_address": "B"}, headers=dispatcher).status_code == 201
    assert client.post(f"{API}/vehicles", json=vehicle, headers=login(client, "owner")).status_code == 201


def test_other_organizations_see_none_of_it(client, db):
    seed(db)
    other = auth(register(client, "boss@real-company.com", "Real Co")["access_token"])
    assert client.get(f"{API}/vehicles", headers=other).json()["total"] == 0
    assert client.get(f"{API}/deliveries", headers=other).json()["total"] == 0
    assert client.get(f"{API}/dashboard", headers=other).json()["has_data"] is False


def test_seeding_twice_changes_nothing(db):
    seed(db)
    again = seed(db)
    assert again["status"] == "exists"
    assert count(db, Vehicle) == 14 and db.scalar(select(func.count()).select_from(Organization)) == 1


def test_reset_rebuilds_the_demo_org_and_leaves_others_alone(client, db):
    seed(db)
    other = auth(register(client, "boss@real-company.com", "Real Co")["access_token"])
    client.post(f"{API}/vehicles", json={"registration": "REAL-1", "manufacturer": "MAN", "model": "TGL"}, headers=other)
    assert seed(db, reset=True)["status"] == "reset"
    assert count(db, Vehicle) == 14  # rebuilt, not doubled
    assert client.get(f"{API}/vehicles", headers=other).json()["total"] == 1
    assert db.scalar(select(func.count()).select_from(User)) == 5  # 4 demo accounts + the real owner
    assert client.get(f"{API}/auth/me", headers=login(client, "owner")).status_code == 200


def test_reset_refuses_when_a_real_user_joined_the_demo_org(client, db):
    seed(db)
    r = client.post(f"{API}/users/invite", json={"email": "newhire@real-company.com", "full_name": "New Hire", "role": "viewer"}, headers=login(client, "owner"))
    assert r.status_code == 201
    with pytest.raises(SeedError, match="non-demo users"):
        seed(db, reset=True)
    assert count(db, Vehicle) == 14  # nothing was deleted


def test_does_not_hijack_demo_emails_used_elsewhere(client, db):
    register(client, DEMO_USERS[0]["email"], "Somebody Else")
    with pytest.raises(SeedError, match="already belongs"):
        seed(db)
    assert db.scalar(select(Organization).where(Organization.name == DEMO_ORG_NAME)) is None


def test_refuses_in_production(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "environment", "production")
    with pytest.raises(SeedError, match="production"):
        seed(db)
    assert db.scalar(select(func.count()).select_from(Organization)) == 0
    assert seed(db, allow_production=True)["status"] == "created"


def test_command_line_is_idempotent(client, db, monkeypatch, capsys):
    from app.seed import __main__ as cli

    monkeypatch.setattr(cli, "SessionLocal", lambda: app.dependency_overrides[get_session_factory]()())
    assert cli.main([]) == 0
    out = capsys.readouterr().out
    assert "created" in out and DEMO_PASSWORD in out and "owner@example.com" in out
    assert cli.main([]) == 0 and "already exists" in capsys.readouterr().out
    assert cli.main(["--reset"]) == 0
    monkeypatch.setattr(get_settings(), "environment", "production")
    assert cli.main(["--reset"]) == 1  # refuses, exit code tells the deploy script


def test_frontend_demo_accounts_match_the_backend():
    ts = pathlib.Path(__file__).resolve().parents[3] / "frontend" / "src" / "config" / "demo.ts"
    if not ts.exists():
        pytest.skip("frontend source not present (backend-only checkout or image)")
    text = ts.read_text()
    assert DEMO_PASSWORD in text
    assert all(u["email"] in text for u in DEMO_USERS)
