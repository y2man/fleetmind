import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.fleet import Lat, Lng, Str120


class GPSCredentialCreate(BaseModel):
    vehicle_id: uuid.UUID
    label: Str120


class GPSCredentialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vehicle_id: uuid.UUID
    label: str
    created_at: datetime
    revoked_at: datetime | None
    last_used_at: datetime | None


class GPSCredentialCreated(GPSCredentialOut):
    token: str


class GPSPositionIn(BaseModel):
    lat: Lat
    lng: Lng
    speed_kph: float | None = Field(default=None, ge=0, le=500)
    heading: float | None = Field(default=None, ge=0, lt=360)
    recorded_at: datetime

    @field_validator("recorded_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_at must include a timezone")
        return value.astimezone(timezone.utc)


class GPSPositionAccepted(BaseModel):
    accepted: bool = True
    vehicle_id: uuid.UUID
    recorded_at: datetime


class TrackingLinkCreate(BaseModel):
    ttl_hours: int = Field(default=168, ge=1, le=2160)


class TrackingLinkCreated(BaseModel):
    id: uuid.UUID
    url: str
    expires_at: datetime


class TrackingLinkOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None


class DeliverySMSIn(BaseModel):
    message: str = Field(min_length=1, max_length=1600)


class DeliverySMSOut(BaseModel):
    message_id: str
    status: str


class PublicTrackingOut(BaseModel):
    reference: str
    status: str
    destination: str
    deadline: datetime | None
    delivered_at: datetime | None
    updated_at: datetime
    expires_at: datetime
