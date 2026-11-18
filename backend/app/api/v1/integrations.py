import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import client_ip, require
from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.models import CustomerTrackingLink, Delivery, GPSDeviceCredential, User, Vehicle, VehicleLocation
from app.schemas.integrations import (
    DeliverySMSIn, DeliverySMSOut, GPSCredentialCreate, GPSCredentialCreated, GPSCredentialOut, GPSPositionAccepted,
    GPSPositionIn, PublicTrackingOut, TrackingLinkCreate, TrackingLinkCreated,
    TrackingLinkOut,
)
from app.services import audit, sms

router = APIRouter(tags=["integrations"])
gps_ingest_limit = rate_limit("gps-ingest", 120, 60)
public_tracking_limit = rate_limit("public-tracking", 60, 60)
sms_send_limit = rate_limit("sms-send", 10, 3600)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/integrations/gps/credentials", response_model=GPSCredentialCreated, status_code=201)
def create_gps_credential(
    body: GPSCredentialCreate,
    request: Request,
    user: User = Depends(require("vehicles:write")),
    db: Session = Depends(get_db),
):
    vehicle = db.scalar(select(Vehicle).where(
        Vehicle.id == body.vehicle_id,
        Vehicle.organization_id == user.organization_id,
    ))
    if vehicle is None:
        raise HTTPException(404, "Vehicle not found")
    raw_token = "fm_gps_" + secrets.token_urlsafe(32)
    row = GPSDeviceCredential(
        organization_id=user.organization_id,
        vehicle_id=vehicle.id,
        token_hash=_token_hash(raw_token),
        label=body.label,
    )
    db.add(row)
    audit.record(
        db, "gps.credential_created", user=user, ip=client_ip(request),
        entity_type="vehicle", entity_id=str(vehicle.id),
        detail={"credential_id": str(row.id), "label": body.label},
    )
    db.commit()
    db.refresh(row)
    return GPSCredentialCreated(
        id=row.id,
        vehicle_id=row.vehicle_id,
        label=row.label,
        created_at=row.created_at,
        revoked_at=row.revoked_at,
        last_used_at=row.last_used_at,
        token=raw_token,
    )


@router.get("/integrations/gps/credentials", response_model=list[GPSCredentialOut])
def list_gps_credentials(user: User = Depends(require("vehicles:read")), db: Session = Depends(get_db)):
    return list(db.scalars(
        select(GPSDeviceCredential)
        .where(GPSDeviceCredential.organization_id == user.organization_id)
        .order_by(GPSDeviceCredential.created_at.desc(), GPSDeviceCredential.id)
    ))


@router.delete("/integrations/gps/credentials/{credential_id}", status_code=204)
def revoke_gps_credential(
    credential_id: uuid.UUID,
    request: Request,
    user: User = Depends(require("vehicles:write")),
    db: Session = Depends(get_db),
):
    row = db.scalar(select(GPSDeviceCredential).where(
        GPSDeviceCredential.id == credential_id,
        GPSDeviceCredential.organization_id == user.organization_id,
    ))
    if row is None:
        raise HTTPException(404, "GPS credential not found")
    if row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        audit.record(
            db, "gps.credential_revoked", user=user, ip=client_ip(request),
            entity_type="vehicle", entity_id=str(row.vehicle_id),
            detail={"credential_id": str(row.id)},
        )
        db.commit()
    return None


@router.post(
    "/integrations/gps/positions",
    response_model=GPSPositionAccepted,
    dependencies=[Depends(gps_ingest_limit)],
)
def ingest_gps_position(
    body: GPSPositionIn,
    x_gps_token: str | None = Header(default=None, alias="X-GPS-Token"),
    db: Session = Depends(get_db),
):
    if not x_gps_token:
        raise HTTPException(401, "GPS device credential required")
    credential = db.scalar(select(GPSDeviceCredential).where(
        GPSDeviceCredential.token_hash == _token_hash(x_gps_token),
        GPSDeviceCredential.revoked_at.is_(None),
    ))
    if credential is None:
        raise HTTPException(401, "GPS device credential is invalid or revoked")
    vehicle = db.scalar(select(Vehicle).where(
        Vehicle.id == credential.vehicle_id,
        Vehicle.organization_id == credential.organization_id,
    ))
    if vehicle is None or vehicle.status == "retired":
        raise HTTPException(404, "Active vehicle not found")

    now = datetime.now(timezone.utc)
    max_age = get_settings().gps_ingest_max_age_seconds
    if body.recorded_at < now - timedelta(seconds=max_age) or body.recorded_at > now + timedelta(minutes=5):
        raise HTTPException(422, "GPS sample timestamp is outside the accepted time window")

    latest = db.scalar(
        select(VehicleLocation)
        .where(
            VehicleLocation.organization_id == credential.organization_id,
            VehicleLocation.vehicle_id == vehicle.id,
            VehicleLocation.is_simulated.is_(False),
        )
        .order_by(VehicleLocation.recorded_at.desc(), VehicleLocation.id.desc())
        .limit(1)
    )
    if latest:
        latest_recorded_at = latest.recorded_at
        if latest_recorded_at.tzinfo is None:
            latest_recorded_at = latest_recorded_at.replace(tzinfo=timezone.utc)
        if body.recorded_at <= latest_recorded_at:
            raise HTTPException(409, "GPS sample is not newer than the latest accepted position")

    db.add(VehicleLocation(
        organization_id=credential.organization_id,
        vehicle_id=vehicle.id,
        lat=body.lat,
        lng=body.lng,
        speed_kph=body.speed_kph,
        heading=body.heading,
        is_simulated=False,
        recorded_at=body.recorded_at,
    ))
    vehicle.last_lat, vehicle.last_lng = body.lat, body.lng
    vehicle.status = "active"
    credential.last_used_at = now
    db.commit()
    return GPSPositionAccepted(vehicle_id=vehicle.id, recorded_at=body.recorded_at)


@router.post(
    "/deliveries/{delivery_id}/tracking-links",
    response_model=TrackingLinkCreated,
    status_code=201,
)
def create_tracking_link(
    delivery_id: uuid.UUID,
    body: TrackingLinkCreate,
    request: Request,
    user: User = Depends(require("deliveries:write")),
    db: Session = Depends(get_db),
):
    delivery = db.scalar(select(Delivery).where(
        Delivery.id == delivery_id,
        Delivery.organization_id == user.organization_id,
    ))
    if delivery is None:
        raise HTTPException(404, "Delivery not found")
    if delivery.status == "cancelled":
        raise HTTPException(409, "Cannot create a tracking link for a cancelled delivery")
    ttl = min(body.ttl_hours, get_settings().tracking_link_max_ttl_hours)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=ttl)
    token = secrets.token_urlsafe(32)
    row = CustomerTrackingLink(
        organization_id=user.organization_id,
        delivery_id=delivery.id,
        token_hash=_token_hash(token),
        expires_at=expires_at,
    )
    db.add(row)
    audit.record(
        db, "delivery.tracking_link_created", user=user, ip=client_ip(request),
        entity_type="delivery", entity_id=str(delivery.id),
        detail={"link_id": str(row.id), "expires_at": expires_at.isoformat()},
    )
    db.commit()
    db.refresh(row)
    base = get_settings().frontend_url.rstrip("/")
    return TrackingLinkCreated(id=row.id, url=f"{base}/track#token={token}", expires_at=row.expires_at)


@router.get(
    "/deliveries/{delivery_id}/tracking-links",
    response_model=list[TrackingLinkOut],
)
def list_tracking_links(
    delivery_id: uuid.UUID,
    user: User = Depends(require("deliveries:read")),
    db: Session = Depends(get_db),
):
    delivery = db.scalar(select(Delivery.id).where(
        Delivery.id == delivery_id,
        Delivery.organization_id == user.organization_id,
    ))
    if delivery is None:
        raise HTTPException(404, "Delivery not found")
    return list(db.scalars(
        select(CustomerTrackingLink)
        .where(
            CustomerTrackingLink.delivery_id == delivery_id,
            CustomerTrackingLink.organization_id == user.organization_id,
        )
        .order_by(CustomerTrackingLink.created_at.desc(), CustomerTrackingLink.id)
    ))


@router.delete("/deliveries/{delivery_id}/tracking-links/{link_id}", status_code=204)
def revoke_tracking_link(
    delivery_id: uuid.UUID,
    link_id: uuid.UUID,
    request: Request,
    user: User = Depends(require("deliveries:write")),
    db: Session = Depends(get_db),
):
    row = db.scalar(select(CustomerTrackingLink).where(
        CustomerTrackingLink.id == link_id,
        CustomerTrackingLink.delivery_id == delivery_id,
        CustomerTrackingLink.organization_id == user.organization_id,
    ))
    if row is None:
        raise HTTPException(404, "Tracking link not found")
    if row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        audit.record(
            db, "delivery.tracking_link_revoked", user=user, ip=client_ip(request),
            entity_type="delivery", entity_id=str(delivery_id),
            detail={"link_id": str(row.id)},
        )
        db.commit()
    return None


@router.get(
    "/public/tracking",
    response_model=PublicTrackingOut,
    dependencies=[Depends(public_tracking_limit)],
)
def public_tracking(
    x_tracking_token: str | None = Header(default=None, alias="X-Tracking-Token"),
    db: Session = Depends(get_db),
):
    if not x_tracking_token or len(x_tracking_token) > 256:
        raise HTTPException(404, "Tracking link is invalid or expired")
    now = datetime.now(timezone.utc)
    link = db.scalar(select(CustomerTrackingLink).where(
        CustomerTrackingLink.token_hash == _token_hash(x_tracking_token),
        CustomerTrackingLink.revoked_at.is_(None),
        CustomerTrackingLink.expires_at > now,
    ))
    if link is None:
        raise HTTPException(404, "Tracking link is invalid or expired")
    delivery = db.scalar(select(Delivery).where(
        Delivery.id == link.delivery_id,
        Delivery.organization_id == link.organization_id,
    ))
    if delivery is None:
        raise HTTPException(404, "Tracking link is invalid or expired")
    return PublicTrackingOut(
        reference=delivery.reference,
        status=delivery.status,
        destination=delivery.dest_address,
        deadline=delivery.deadline,
        delivered_at=delivery.delivered_at,
        updated_at=delivery.updated_at,
        expires_at=link.expires_at,
    )


@router.post(
    "/deliveries/{delivery_id}/sms",
    response_model=DeliverySMSOut,
    status_code=202,
    dependencies=[Depends(sms_send_limit)],
)
def send_delivery_sms(
    delivery_id: uuid.UUID,
    body: DeliverySMSIn,
    request: Request,
    user: User = Depends(require("deliveries:write")),
    db: Session = Depends(get_db),
):
    delivery = db.scalar(select(Delivery).where(
        Delivery.id == delivery_id,
        Delivery.organization_id == user.organization_id,
    ))
    if delivery is None:
        raise HTTPException(404, "Delivery not found")
    if not delivery.customer_phone:
        raise HTTPException(409, "This delivery has no customer phone number")
    if len(body.message.strip()) == 0:
        raise HTTPException(422, "Message cannot be blank")
    try:
        result = sms.send_customer_sms(delivery.customer_phone, body.message.strip())
    except sms.SMSNotConfigured as exc:
        raise HTTPException(503, "AfroMessage is not configured; set its API key and identifier ID") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except sms.SMSProviderError as exc:
        raise HTTPException(502, "AfroMessage did not accept the SMS") from exc

    audit.record(
        db, "delivery.sms_accepted", user=user, ip=client_ip(request),
        entity_type="delivery", entity_id=str(delivery.id),
        detail={"provider": "afromessage", "message_id": result["message_id"], "status": result["status"]},
    )
    db.commit()
    return DeliverySMSOut(**result)
