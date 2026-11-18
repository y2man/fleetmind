from datetime import datetime, timedelta, timezone
import uuid

from tests.conftest import auth, register


def _create_vehicle(client, headers):
    response = client.post(
        "/api/v1/vehicles",
        headers=headers,
        json={"registration": "GPS-101", "manufacturer": "Test", "model": "Van", "status": "idle"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_delivery(client, headers):
    response = client.post(
        "/api/v1/deliveries",
        headers=headers,
        json={"pickup_address": "Depot", "dest_address": "Customer", "customer_phone": "+251911000000"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_gps_credentials_ingest_new_positions_and_revoke(client):
    owner = register(client)
    headers = auth(owner["access_token"])
    vehicle_id = _create_vehicle(client, headers)
    created = client.post(
        "/api/v1/integrations/gps/credentials",
        headers=headers,
        json={"vehicle_id": vehicle_id, "label": "Vehicle tracker"},
    )
    assert created.status_code == 201, created.text
    credential = created.json()
    token = credential["token"]
    assert token.startswith("fm_gps_") and len(token) > 40
    assert client.get("/api/v1/integrations/gps/credentials", headers=headers).json()[0]["id"] == credential["id"]
    assert "token" not in client.get("/api/v1/integrations/gps/credentials", headers=headers).json()[0]

    sample_time = datetime.now(timezone.utc).isoformat()
    accepted = client.post(
        "/api/v1/integrations/gps/positions",
        headers={"X-GPS-Token": token},
        json={"lat": 9.02, "lng": 38.73, "speed_kph": 27.5, "heading": 180, "recorded_at": sample_time},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["accepted"] is True
    duplicate = client.post(
        "/api/v1/integrations/gps/positions",
        headers={"X-GPS-Token": token},
        json={"lat": 9.03, "lng": 38.74, "recorded_at": sample_time},
    )
    assert duplicate.status_code == 409
    positions = client.get("/api/v1/tracking/vehicles", headers=headers).json()
    assert len(positions) == 1 and positions[0]["lat"] == 9.02 and positions[0]["lng"] == 38.73 and positions[0]["simulated"] is False
    history = client.get(f"/api/v1/tracking/vehicles/{vehicle_id}/history", headers=headers).json()
    assert len(history) == 1 and history[0]["simulated"] is False

    revoked = client.delete(f'/api/v1/integrations/gps/credentials/{credential["id"]}', headers=headers)
    assert revoked.status_code == 204
    denied = client.post(
        "/api/v1/integrations/gps/positions",
        headers={"X-GPS-Token": token},
        json={"lat": 9.04, "lng": 38.75, "recorded_at": (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat()},
    )
    assert denied.status_code == 401


def test_gps_ingestion_validates_credentials_timestamp_and_tenant(client):
    owner_a = register(client, "a@a.com", "A")
    owner_b = register(client, "b@b.com", "B")
    vehicle_id = _create_vehicle(client, auth(owner_a["access_token"]))
    credential = client.post(
        "/api/v1/integrations/gps/credentials",
        headers=auth(owner_a["access_token"]),
        json={"vehicle_id": vehicle_id, "label": "tracker"},
    ).json()
    endpoint = "/api/v1/integrations/gps/positions"

    assert client.post(endpoint, json={"lat": 9, "lng": 38, "recorded_at": datetime.now(timezone.utc).isoformat()}).status_code == 401
    assert client.post(
        endpoint,
        headers={"X-GPS-Token": "invalid"},
        json={"lat": 9, "lng": 38, "recorded_at": datetime.now(timezone.utc).isoformat()},
    ).status_code == 401
    assert client.post(
        endpoint,
        headers={"X-GPS-Token": credential["token"]},
        json={"lat": 100, "lng": 38, "recorded_at": datetime.now(timezone.utc).isoformat()},
    ).status_code == 422
    assert client.get("/api/v1/vehicles", headers=auth(owner_b["access_token"])).json()["total"] == 0
    assert client.get("/api/v1/tracking/vehicles", headers=auth(owner_b["access_token"])).json() == []


def test_customer_tracking_link_is_scoped_revocable_and_expires(client, monkeypatch):
    from app.core.config import get_settings
    from app.core.database import get_session_factory
    from app.main import app
    from app.models import CustomerTrackingLink

    monkeypatch.setattr(get_settings(), "frontend_url", "https://fleet.example.test")
    owner = register(client)
    headers = auth(owner["access_token"])
    delivery_id = _create_delivery(client, headers)
    created = client.post(
        f"/api/v1/deliveries/{delivery_id}/tracking-links",
        headers=headers,
        json={"ttl_hours": 24},
    )
    assert created.status_code == 201, created.text
    data = created.json()
    assert data["url"].startswith("https://fleet.example.test/track#token=")
    token = data["url"].split("#token=", 1)[1]
    assert token
    listed = client.get(f"/api/v1/deliveries/{delivery_id}/tracking-links", headers=headers)
    assert listed.status_code == 200 and len(listed.json()) == 1
    assert "token" not in listed.json()[0] and "token_hash" not in listed.json()[0]

    public = client.get("/api/v1/public/tracking", headers={"X-Tracking-Token": token})
    assert public.status_code == 200
    assert public.json()["destination"] == "Customer"
    assert "customer_phone" not in public.json() and "organization_id" not in public.json()

    other = register(client, "other@a.com", "Other")
    assert client.delete(
        f'/api/v1/deliveries/{delivery_id}/tracking-links/{data["id"]}',
        headers=auth(other["access_token"]),
    ).status_code == 404

    factory = app.dependency_overrides[get_session_factory]()
    with factory() as db:
        link = db.get(CustomerTrackingLink, uuid.UUID(data["id"]))
        link.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    assert client.get("/api/v1/public/tracking", headers={"X-Tracking-Token": token}).status_code == 404


def test_customer_tracking_link_revocation_and_cancelled_delivery(client):
    owner = register(client)
    headers = auth(owner["access_token"])
    delivery_id = _create_delivery(client, headers)
    created = client.post(f"/api/v1/deliveries/{delivery_id}/tracking-links", headers=headers, json={}).json()
    token = created["url"].split("#token=", 1)[1]
    assert client.delete(
        f'/api/v1/deliveries/{delivery_id}/tracking-links/{created["id"]}',
        headers=headers,
    ).status_code == 204
    assert client.get("/api/v1/public/tracking", headers={"X-Tracking-Token": token}).status_code == 404

    client.patch(f"/api/v1/deliveries/{delivery_id}", headers=headers, json={"status": "cancelled"})
    assert client.post(f"/api/v1/deliveries/{delivery_id}/tracking-links", headers=headers, json={}).status_code == 409


def test_delivery_sms_uses_afromessage_and_audits_acceptance(client, monkeypatch):
    from app.core.config import get_settings
    from app.services import sms

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"acknowledge": "success", "response": {"status": "Send in progress...", "message_id": "sms-123"}}

    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr(get_settings(), "afromessage_api_key", "test-token")
    monkeypatch.setattr(get_settings(), "afromessage_identifier_id", "test-identifier")
    monkeypatch.setattr(get_settings(), "afromessage_sender", "FleetMind")
    monkeypatch.setattr(sms.httpx, "post", fake_post)
    owner = register(client)
    headers = auth(owner["access_token"])
    delivery_id = _create_delivery(client, headers)

    sent = client.post(
        f"/api/v1/deliveries/{delivery_id}/sms",
        headers=headers,
        json={"message": "Your delivery is on its way."},
    )
    assert sent.status_code == 202, sent.text
    assert sent.json() == {"message_id": "sms-123", "status": "Send in progress..."}
    assert calls[0][0] == "https://api.afromessage.com/api/send"
    assert calls[0][1]["headers"]["Authorization"] == "Bearer test-token"
    assert calls[0][1]["json"] == {
        "from": "test-identifier",
        "sender": "FleetMind",
        "to": "+251911000000",
        "message": "Your delivery is on its way.",
    }

    audit_rows = client.get("/api/v1/audit-logs", headers=headers).json()
    sms_audit = next(row for row in audit_rows if row["action"] == "delivery.sms_accepted")
    assert sms_audit["entity_id"] == delivery_id


def test_delivery_sms_handles_configuration_provider_and_tenant_errors(client, monkeypatch):
    from app.core.config import get_settings
    from app.services import sms

    owner = register(client)
    headers = auth(owner["access_token"])
    delivery_id = _create_delivery(client, headers)
    endpoint = f"/api/v1/deliveries/{delivery_id}/sms"
    body = {"message": "A delivery update"}
    assert client.post(endpoint, headers=headers, json=body).status_code == 503

    other = register(client, "other@a.com", "Other")
    assert client.post(endpoint, headers=auth(other["access_token"]), json=body).status_code == 404

    monkeypatch.setattr(get_settings(), "afromessage_api_key", "test-token")
    monkeypatch.setattr(get_settings(), "afromessage_identifier_id", "test-identifier")
    monkeypatch.setattr(sms.httpx, "post", lambda *args, **kwargs: (_ for _ in ()).throw(sms.httpx.ConnectError("offline")))
    assert client.post(endpoint, headers=headers, json=body).status_code == 502

    invalid_phone = client.patch(
        f"/api/v1/deliveries/{delivery_id}", headers=headers, json={"customer_phone": "not-a-phone"}
    )
    assert invalid_phone.status_code == 200
    assert client.post(endpoint, headers=headers, json=body).status_code == 422
