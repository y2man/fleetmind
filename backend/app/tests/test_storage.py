import httpx
import pytest

from app.core.config import get_settings
from app.services import storage


def configure_storage(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "supabase_url", "https://project.supabase.co/")
    monkeypatch.setattr(settings, "supabase_service_role_key", "test-service-role")
    monkeypatch.setattr(settings, "supabase_bucket", "fleetmind-documents")
    return settings


def test_upload_download_and_delete_use_private_storage_auth(monkeypatch):
    configure_storage(monkeypatch)
    calls = []

    class Response:
        content = b"private object"

        def raise_for_status(self):
            pass

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return Response()

    monkeypatch.setattr(storage.httpx, "request", fake_request)

    key = "org-id/delivery-id/proof.pdf"
    storage.upload_object(key, b"%PDF", "application/pdf")
    assert storage.download_object(key) == b"private object"
    storage.delete_object(key)

    assert [call[0] for call in calls] == ["POST", "GET", "DELETE"]
    object_url = "https://project.supabase.co/storage/v1/object/fleetmind-documents/org-id/delivery-id/proof.pdf"
    assert calls[0][1] == object_url and calls[1][1] == object_url
    assert calls[2][1] == "https://project.supabase.co/storage/v1/object/fleetmind-documents"
    assert all(call[2]["headers"]["Authorization"] == "Bearer test-service-role" for call in calls)
    assert calls[0][2]["headers"]["x-upsert"] == "false"
    assert calls[0][2]["content"] == b"%PDF"
    assert calls[2][2]["json"] == {"prefixes": [key]}


def test_storage_provider_errors_do_not_include_credentials(monkeypatch):
    configure_storage(monkeypatch)

    def fail_request(*args, **kwargs):
        request = httpx.Request("GET", "https://project.supabase.co/storage/v1/object/private/file")
        response = httpx.Response(403, request=request)
        raise httpx.HTTPStatusError("provider rejected request", request=request, response=response)

    monkeypatch.setattr(storage.httpx, "request", fail_request)
    with pytest.raises(storage.StorageProviderError) as caught:
        storage.download_object("org/delivery/proof.pdf")
    assert "test-service-role" not in str(caught.value)


def test_storage_requires_backend_configuration(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "supabase_url", "")
    monkeypatch.setattr(settings, "supabase_service_role_key", "")
    with pytest.raises(storage.StorageNotConfigured):
        storage.upload_object("org/delivery/proof.pdf", b"%PDF", "application/pdf")
