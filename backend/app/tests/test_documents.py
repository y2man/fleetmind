from tests.conftest import auth, register


PDF = b"%PDF-1.7\nproof"


def create_delivery(client, token):
    response = client.post(
        "/api/v1/deliveries",
        headers=auth(token),
        json={"pickup_address": "Depot", "dest_address": "Customer"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_proof_upload_list_and_download_are_tenant_scoped(client, monkeypatch):
    from app.services import storage

    uploads = []
    monkeypatch.setattr(storage, "upload_object", lambda key, data, content_type: uploads.append((key, data, content_type)))
    monkeypatch.setattr(storage, "download_object", lambda key: PDF)
    owner = register(client)
    delivery_id = create_delivery(client, owner["access_token"])

    uploaded = client.post(
        f"/api/v1/deliveries/{delivery_id}/proof",
        params={"filename": "delivery proof.pdf"},
        headers={**auth(owner["access_token"]), "Content-Type": "application/pdf"},
        content=PDF,
    )
    assert uploaded.status_code == 201, uploaded.text
    document = uploaded.json()
    assert document["filename"] == "delivery proof.pdf"
    assert document["content_type"] == "application/pdf"
    assert document["size_bytes"] == len(PDF)
    assert "storage_key" not in document and len(uploads) == 1
    assert uploads[0][0].startswith(f'{owner["user"]["organization"]["id"]}/{delivery_id}/')

    listed = client.get(f"/api/v1/deliveries/{delivery_id}/proof", headers=auth(owner["access_token"]))
    assert listed.status_code == 200 and [item["id"] for item in listed.json()] == [document["id"]]

    downloaded = client.get(
        f'/api/v1/deliveries/{delivery_id}/proof/{document["id"]}/content',
        headers=auth(owner["access_token"]),
    )
    assert downloaded.status_code == 200 and downloaded.content == PDF
    assert "filename*=UTF-8''delivery%20proof.pdf" in downloaded.headers["content-disposition"]

    other_org = register(client, "other@a.com", "Other Org")
    other_delivery = create_delivery(client, other_org["access_token"])
    hidden = client.get(
        f'/api/v1/deliveries/{delivery_id}/proof/{document["id"]}/content',
        headers=auth(other_org["access_token"]),
    )
    assert hidden.status_code == 404
    assert client.get(f"/api/v1/deliveries/{delivery_id}/proof", headers=auth(other_org["access_token"])).status_code == 404
    assert other_delivery != delivery_id


def test_proof_upload_rejects_mismatched_mime_and_oversized_content(client, monkeypatch):
    from app.core.config import get_settings
    from app.services import storage

    owner = register(client)
    delivery_id = create_delivery(client, owner["access_token"])
    uploads = []
    monkeypatch.setattr(storage, "upload_object", lambda *args: uploads.append(args))
    headers = auth(owner["access_token"])

    mismatch = client.post(
        f"/api/v1/deliveries/{delivery_id}/proof",
        params={"filename": "proof.pdf"},
        headers={**headers, "Content-Type": "application/pdf"},
        content=b"not a pdf",
    )
    assert mismatch.status_code == 415

    monkeypatch.setattr(get_settings(), "document_max_bytes", 4)
    oversized = client.post(
        f"/api/v1/deliveries/{delivery_id}/proof",
        params={"filename": "proof.pdf"},
        headers={**headers, "Content-Type": "application/pdf"},
        content=PDF,
    )
    assert oversized.status_code == 413
    assert uploads == []


def test_proof_upload_reports_missing_storage_configuration(client, monkeypatch):
    from app.core.config import get_settings

    owner = register(client)
    delivery_id = create_delivery(client, owner["access_token"])
    settings = get_settings()
    monkeypatch.setattr(settings, "supabase_url", "")
    monkeypatch.setattr(settings, "supabase_service_role_key", "")
    response = client.post(
        f"/api/v1/deliveries/{delivery_id}/proof",
        params={"filename": "proof.pdf"},
        headers={**auth(owner["access_token"]), "Content-Type": "application/pdf"},
        content=PDF,
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "Private document storage is not configured"
