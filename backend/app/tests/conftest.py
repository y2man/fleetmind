import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ENVIRONMENT"] = "development"
os.environ["SECRET_KEY"] = "tests-only-secret-key-that-is-at-least-32-bytes"
os.environ["RESEND_API_KEY"] = ""
os.environ["EMAIL_FROM"] = ""
os.environ["SMTP_HOST"] = ""
os.environ["GROQ_API_KEY"] = ""
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""
os.environ["AFROMESSAGE_API_KEY"] = ""
os.environ["AFROMESSAGE_IDENTIFIER_ID"] = ""
os.environ["AFROMESSAGE_SENDER"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core import rate_limit  # noqa: E402
from app.core.database import Base, get_db, get_session_factory  # noqa: E402
import app.models  # noqa: E402,F401
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):  # SQLite ignores ON DELETE SET NULL / CASCADE unless this is enabled (Postgres always enforces)
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    app.dependency_overrides[get_session_factory] = lambda: Session  # WebSocket code opens its own sessions
    rate_limit.reset()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


PW = "Sup3rSecretPw"


def register(client, email="owner@a.com", org="Acme Logistics"):
    r = client.post("/api/v1/auth/register", json={"email": email, "password": PW, "full_name": "Test User", "organization_name": org})
    assert r.status_code == 201, r.text
    return r.json()


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def invite_and_login(client, owner_token, email, role):
    r = client.post("/api/v1/users/invite", json={"email": email, "full_name": "Invitee", "role": role}, headers=auth(owner_token))
    assert r.status_code == 201, r.text
    reset_token = r.json()["dev_link"].split("token=")[1]
    assert client.post("/api/v1/auth/reset-password", json={"token": reset_token, "new_password": PW}).status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": email, "password": PW})
    assert login.status_code == 200
    return login.json()["access_token"]
