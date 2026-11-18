import asyncio
import logging
import uuid
from pathlib import PurePosixPath
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import client_ip, require
from app.core.config import get_settings
from app.core.database import get_db
from app.models import Delivery, DeliveryDocument, User
from app.schemas.documents import DeliveryDocumentOut
from app.services import audit, storage

logger = logging.getLogger("fleetmind.documents")
router = APIRouter(tags=["delivery documents"])

ALLOWED_TYPES = {
    ".pdf": ("application/pdf", lambda data: data.startswith(b"%PDF-")),
    ".jpg": ("image/jpeg", lambda data: data.startswith(b"\xff\xd8\xff")),
    ".jpeg": ("image/jpeg", lambda data: data.startswith(b"\xff\xd8\xff")),
    ".png": ("image/png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    ".webp": ("image/webp", lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"),
}


def _delivery(db: Session, user: User, delivery_id: uuid.UUID) -> Delivery:
    row = db.scalar(select(Delivery).where(
        Delivery.id == delivery_id,
        Delivery.organization_id == user.organization_id,
    ))
    if row is None:
        raise HTTPException(404, "Delivery not found")
    return row


async def _read_upload(request: Request, max_bytes: int) -> bytes:
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > max_bytes:
            raise HTTPException(413, "Proof file exceeds the upload size limit")
        data.extend(chunk)
    return bytes(data)


def _validated_file(filename: str, content_type: str, data: bytes) -> tuple[str, str]:
    safe_name = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not safe_name or len(safe_name) > 255 or any(ord(char) < 32 for char in safe_name):
        raise HTTPException(422, "Invalid file name")
    extension = PurePosixPath(safe_name).suffix.lower()
    expected = ALLOWED_TYPES.get(extension)
    if expected is None or content_type.split(";", 1)[0].strip().lower() != expected[0]:
        raise HTTPException(415, "Proof must be a PDF, JPEG, PNG, or WebP file")
    if not expected[1](data):
        raise HTTPException(415, "File content does not match the declared type")
    return safe_name, expected[0]


@router.post(
    "/deliveries/{delivery_id}/proof",
    response_model=DeliveryDocumentOut,
    status_code=201,
)
async def upload_proof(
    delivery_id: uuid.UUID,
    request: Request,
    filename: str = Query(..., min_length=1, max_length=255),
    user: User = Depends(require("deliveries:write")),
    db: Session = Depends(get_db),
):
    _delivery(db, user, delivery_id)
    settings = get_settings()
    data = await _read_upload(request, settings.document_max_bytes)
    safe_name, content_type = _validated_file(filename, request.headers.get("content-type", ""), data)
    document_id = uuid.uuid4()
    storage_key = f"{user.organization_id}/{delivery_id}/{document_id}{PurePosixPath(safe_name).suffix.lower()}"
    try:
        await asyncio.to_thread(storage.upload_object, storage_key, data, content_type)
    except storage.StorageNotConfigured as exc:
        raise HTTPException(503, "Private document storage is not configured") from exc
    except storage.StorageProviderError as exc:
        logger.error("Proof upload failed for delivery %s", delivery_id)
        raise HTTPException(502, "Proof could not be uploaded to private storage") from exc

    row = DeliveryDocument(
        id=document_id,
        organization_id=user.organization_id,
        delivery_id=delivery_id,
        uploaded_by=user.id,
        storage_key=storage_key,
        filename=safe_name,
        content_type=content_type,
        size_bytes=len(data),
    )
    db.add(row)
    audit.record(
        db, "delivery.proof_uploaded", user=user, ip=client_ip(request),
        entity_type="delivery", entity_id=str(delivery_id),
        detail={"document_id": str(document_id), "filename": safe_name, "size_bytes": len(data)},
    )
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        try:
            await asyncio.to_thread(storage.delete_object, storage_key)
        except (storage.StorageNotConfigured, storage.StorageProviderError) as cleanup_exc:
            logger.error("Could not clean up proof object after metadata failure (%s)", type(cleanup_exc).__name__)
        logger.exception("Could not persist proof metadata for delivery %s", delivery_id)
        raise HTTPException(500, "Proof metadata could not be saved") from exc
    db.refresh(row)
    return row


@router.get("/deliveries/{delivery_id}/proof", response_model=list[DeliveryDocumentOut])
def list_proofs(
    delivery_id: uuid.UUID,
    user: User = Depends(require("deliveries:read")),
    db: Session = Depends(get_db),
):
    _delivery(db, user, delivery_id)
    return list(db.scalars(
        select(DeliveryDocument)
        .where(
            DeliveryDocument.delivery_id == delivery_id,
            DeliveryDocument.organization_id == user.organization_id,
        )
        .order_by(DeliveryDocument.created_at.desc(), DeliveryDocument.id)
    ))


@router.get("/deliveries/{delivery_id}/proof/{document_id}/content")
def download_proof(
    delivery_id: uuid.UUID,
    document_id: uuid.UUID,
    user: User = Depends(require("deliveries:read")),
    db: Session = Depends(get_db),
):
    row = db.scalar(select(DeliveryDocument).where(
        DeliveryDocument.id == document_id,
        DeliveryDocument.delivery_id == delivery_id,
        DeliveryDocument.organization_id == user.organization_id,
    ))
    if row is None:
        raise HTTPException(404, "Proof document not found")
    _delivery(db, user, delivery_id)
    try:
        content = storage.download_object(row.storage_key)
    except storage.StorageNotConfigured as exc:
        raise HTTPException(503, "Private document storage is not configured") from exc
    except storage.StorageProviderError as exc:
        logger.error("Proof download failed for document %s", document_id)
        raise HTTPException(502, "Proof could not be retrieved from private storage") from exc
    return Response(
        content=content,
        media_type=row.content_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(row.filename)}"},
    )


@router.delete("/deliveries/{delivery_id}/proof/{document_id}", status_code=204)
def delete_proof(
    delivery_id: uuid.UUID,
    document_id: uuid.UUID,
    request: Request,
    user: User = Depends(require("deliveries:write")),
    db: Session = Depends(get_db),
):
    row = db.scalar(select(DeliveryDocument).where(
        DeliveryDocument.id == document_id,
        DeliveryDocument.delivery_id == delivery_id,
        DeliveryDocument.organization_id == user.organization_id,
    ))
    if row is None:
        raise HTTPException(404, "Proof document not found")
    try:
        storage.delete_object(row.storage_key)
    except storage.StorageNotConfigured as exc:
        raise HTTPException(503, "Private document storage is not configured") from exc
    except storage.StorageProviderError as exc:
        logger.error("Proof delete failed for document %s", document_id)
        raise HTTPException(502, "Proof could not be deleted from private storage") from exc
    audit.record(
        db, "delivery.proof_deleted", user=user, ip=client_ip(request),
        entity_type="delivery", entity_id=str(delivery_id),
        detail={"document_id": str(document_id)},
    )
    db.delete(row)
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Could not delete proof metadata for delivery %s", delivery_id)
        raise HTTPException(500, "Proof metadata could not be deleted") from exc
    return Response(status_code=204)
