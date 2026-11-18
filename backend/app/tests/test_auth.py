from app.core.config import get_settings
from app.services import auth_service
from tests.conftest import PW, auth, invite_and_login, register


def test_register_and_me(client):
    d = register(client)
    assert d["user"]["role"] == "owner" and "org:manage" in d["user"]["permissions"]
    me = client.get("/api/v1/auth/me", headers=auth(d["access_token"]))
    assert me.status_code == 200 and me.json()["organization"]["name"] == "Acme Logistics"


def test_weak_password_rejected(client):
    r = client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "short", "full_name": "A", "organization_name": "O"})
    assert r.status_code == 422


def test_duplicate_email(client):
    register(client)
    r = client.post("/api/v1/auth/register", json={"email": "OWNER@a.com", "password": PW, "full_name": "A", "organization_name": "O"})
    assert r.status_code == 409


def test_login_and_wrong_password(client):
    register(client)
    assert client.post("/api/v1/auth/login", json={"email": "owner@a.com", "password": "WrongPassw0rd"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "nobody@a.com", "password": PW}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "owner@a.com", "password": PW}).status_code == 200


def test_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers=auth("garbage")).status_code == 401


def test_refresh_cookie(client):
    register(client)
    r = client.post("/api/v1/auth/refresh")
    assert r.status_code == 200 and r.json()["access_token"]
    client.post("/api/v1/auth/logout")
    client.cookies.clear()
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_password_reset_single_use(client):
    register(client)
    assert client.post("/api/v1/auth/forgot-password", json={"email": "ghost@a.com"}).json()["dev_link"] is None
    token = client.post("/api/v1/auth/forgot-password", json={"email": "owner@a.com"}).json()["dev_link"].split("token=")[1]
    new = "Br4ndNewPassword"
    assert client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": new}).status_code == 200
    assert client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "An0therPassword"}).status_code == 400
    assert client.post("/api/v1/auth/login", json={"email": "owner@a.com", "password": new}).status_code == 200


def test_email_verification(client):
    d = register(client)
    assert d["user"]["email_verified"] is False
    token = d["dev_link"].split("token=")[1]
    assert client.post("/api/v1/auth/verify-email", json={"token": token}).status_code == 200
    assert client.get("/api/v1/auth/me", headers=auth(d["access_token"])).json()["email_verified"] is True


def test_successful_email_provider_does_not_return_development_token(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "resend_api_key", "test-key")
    monkeypatch.setattr(auth_service, "send_email", lambda *args: True)
    assert register(client)["dev_link"] is None


def test_failed_email_provider_returns_development_link(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "resend_api_key", "test-key")
    monkeypatch.setattr(auth_service, "send_email", lambda *args: False)
    assert register(client)["dev_link"].startswith("http://localhost:5173/verify-email?token=")


def test_celery_email_backend_queues_verification_message(client, monkeypatch):
    from app.tasks.email import deliver_email

    calls = []
    monkeypatch.setattr(get_settings(), "email_delivery_backend", "celery")
    monkeypatch.setattr(deliver_email, "delay", lambda *args: calls.append(args))
    result = register(client)
    assert result["dev_link"] is None
    assert len(calls) == 1
    assert calls[0][0:2] == ("owner@a.com", "Verify your FleetMind email")


def test_rbac_and_audit(client):
    owner = register(client)["access_token"]
    viewer = invite_and_login(client, owner, "v@a.com", "viewer")
    assert client.get("/api/v1/audit-logs", headers=auth(viewer)).status_code == 403
    assert client.get("/api/v1/users", headers=auth(viewer)).status_code == 403
    assert client.patch("/api/v1/organization", json={"name": "X"}, headers=auth(viewer)).status_code == 403
    logs = client.get("/api/v1/audit-logs", headers=auth(owner)).json()
    assert {"auth.register", "user.invited", "auth.login"} <= {x["action"] for x in logs}


def test_organization_isolation(client):
    a = register(client, "a@a.com", "Org A")["access_token"]
    b = register(client, "b@b.com", "Org B")["access_token"]
    assert {u["email"] for u in client.get("/api/v1/users", headers=auth(a)).json()} == {"a@a.com"}
    b_id = client.get("/api/v1/users", headers=auth(b)).json()[0]["id"]
    assert client.patch(f"/api/v1/users/{b_id}", json={"role": "viewer"}, headers=auth(a)).status_code == 404
    actions = [x["action"] for x in client.get("/api/v1/audit-logs", headers=auth(a)).json()]
    assert actions.count("auth.register") == 1


def test_role_change_rules(client):
    owner = register(client)["access_token"]
    invite_and_login(client, owner, "d@a.com", "dispatcher")
    members = client.get("/api/v1/users", headers=auth(owner)).json()
    me = next(m for m in members if m["role_name"] == "owner")
    d = next(m for m in members if m["email"] == "d@a.com")
    assert client.patch(f"/api/v1/users/{me['id']}", json={"role": "viewer"}, headers=auth(owner)).status_code == 400
    assert client.patch(f"/api/v1/users/{d['id']}", json={"role": "owner"}, headers=auth(owner)).status_code == 422
    assert client.patch(f"/api/v1/users/{d['id']}", json={"role": "viewer"}, headers=auth(owner)).json()["role_name"] == "viewer"


def test_rate_limit(client):
    codes = [client.post("/api/v1/auth/register", json={"email": f"u{i}@x.com", "password": PW, "full_name": "A", "organization_name": "O"}).status_code for i in range(6)]
    assert codes[:5] == [201] * 5 and codes[5] == 429


def test_redis_rate_limit_uses_shared_counter(client, monkeypatch):
    from app.core import rate_limit

    class FakeRedis:
        calls = 0

        def eval(self, _script, _key_count, key, *_args):
            self.calls += 1
            assert key.startswith("fleetmind:rate-limit:register:")
            return [1, 0] if self.calls == 1 else [0, 7]

    fake = FakeRedis()
    monkeypatch.setattr(get_settings(), "rate_limit_backend", "redis")
    monkeypatch.setattr(rate_limit, "_redis", fake)
    payload = {"email": "redis@x.com", "password": PW, "full_name": "A", "organization_name": "O"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    limited = client.post("/api/v1/auth/register", json={**payload, "email": "redis2@x.com"})
    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "7"


def test_redis_rate_limit_fails_closed_when_redis_is_unavailable(client, monkeypatch):
    from redis.exceptions import ConnectionError
    from app.core import rate_limit

    class UnavailableRedis:
        def eval(self, *_args):
            raise ConnectionError("unavailable")

    monkeypatch.setattr(get_settings(), "rate_limit_backend", "redis")
    monkeypatch.setattr(rate_limit, "_redis", UnavailableRedis())
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "redis@x.com", "password": PW, "full_name": "A", "organization_name": "O"},
    )
    assert response.status_code == 503
