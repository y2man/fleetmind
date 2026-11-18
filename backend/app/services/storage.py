from urllib.parse import quote

import httpx

from app.core.config import get_settings


class StorageNotConfigured(Exception):
    pass


class StorageProviderError(Exception):
    pass


def _request(method: str, storage_key: str, *, content: bytes | None = None, content_type: str | None = None) -> httpx.Response:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key or not settings.supabase_bucket:
        raise StorageNotConfigured("Supabase Storage is not configured")

    bucket = quote(settings.supabase_bucket, safe="")
    key = quote(storage_key, safe="/")
    url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{key}"
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }
    if content_type:
        headers["Content-Type"] = content_type
    if method == "POST":
        headers["x-upsert"] = "false"
    try:
        response = httpx.request(method, url, headers=headers, content=content, timeout=30.0)
        response.raise_for_status()
        return response
    except httpx.HTTPError as exc:
        raise StorageProviderError("Supabase Storage request failed") from exc


def upload_object(storage_key: str, content: bytes, content_type: str) -> None:
    _request("POST", storage_key, content=content, content_type=content_type)


def download_object(storage_key: str) -> bytes:
    return _request("GET", storage_key).content


def delete_object(storage_key: str) -> None:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key or not settings.supabase_bucket:
        raise StorageNotConfigured("Supabase Storage is not configured")
    bucket = quote(settings.supabase_bucket, safe="")
    url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{bucket}"
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }
    try:
        response = httpx.request("DELETE", url, headers=headers, json={"prefixes": [storage_key]}, timeout=30.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise StorageProviderError("Supabase Storage delete failed") from exc
