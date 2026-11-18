import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import DemoMixin, IdMixin, OrgMixin, TimestampMixin, in_list, utcnow

VEHICLE_STATUS = ["active", "idle", "maintenance", "retired"]
FUEL_TYPES = ["diesel", "petrol", "electric", "hybrid", "cng"]
DRIVER_STATUS = ["available", "on_duty", "off_duty", "on_leave"]
DELIVERY_STATUS = ["pending", "assigned", "in_transit", "delivered", "delayed", "cancelled"]
ROUTE_STATUS = ["draft", "planned", "in_progress", "completed"]
MAINT_STATUS = ["scheduled", "in_progress", "completed", "cancelled"]
SEVERITY = ["info", "warning", "critical"]


def fk(table: str, nullable: bool = False, ondelete: str | None = None):
    return mapped_column(Uuid, ForeignKey(f"{table}.id", ondelete=ondelete), nullable=nullable, index=True)


class Driver(IdMixin, TimestampMixin, OrgMixin, DemoMixin, Base):
    __tablename__ = "drivers"
    __table_args__ = (UniqueConstraint("organization_id", "license_number"), in_list("availability", DRIVER_STATUS, "ck_driver_status"))
    full_name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str | None] = mapped_column(String(254))
    phone: Mapped[str | None] = mapped_column(String(40))
    license_number: Mapped[str] = mapped_column(String(64))
    license_expiry: Mapped[date | None] = mapped_column(Date)
    availability: Mapped[str] = mapped_column(String(16), default="available")
    safety_score: Mapped[float | None] = mapped_column(Float)


class Vehicle(IdMixin, TimestampMixin, OrgMixin, DemoMixin, Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        UniqueConstraint("organization_id", "registration"),
        Index("ix_vehicle_org_status", "organization_id", "status"),
        in_list("status", VEHICLE_STATUS, "ck_vehicle_status"),
        in_list("fuel_type", FUEL_TYPES, "ck_vehicle_fuel"),
    )
    registration: Mapped[str] = mapped_column(String(32))
    manufacturer: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(80))
    year: Mapped[int | None]
    fuel_type: Mapped[str] = mapped_column(String(16), default="diesel")
    status: Mapped[str] = mapped_column(String(16), default="idle")
    mileage_km: Mapped[int] = mapped_column(default=0)
    capacity_kg: Mapped[int | None]
    driver_id: Mapped[uuid.UUID | None] = fk("drivers", True, "SET NULL")
    insurance_expiry: Mapped[date | None] = mapped_column(Date)
    registration_expiry: Mapped[date | None] = mapped_column(Date)
    last_lat: Mapped[float | None] = mapped_column(Float)
    last_lng: Mapped[float | None] = mapped_column(Float)


class Route(IdMixin, TimestampMixin, OrgMixin, Base):
    __tablename__ = "routes"
    __table_args__ = (in_list("status", ROUTE_STATUS, "ck_route_status"),)
    name: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(16), default="draft")
    vehicle_id: Mapped[uuid.UUID | None] = fk("vehicles", True, "SET NULL")
    driver_id: Mapped[uuid.UUID | None] = fk("drivers", True, "SET NULL")
    total_distance_km: Mapped[float | None] = mapped_column(Float)
    est_duration_min: Mapped[int | None]
    optimization_notes: Mapped[dict | None] = mapped_column(JSON)  # assumptions behind savings estimates


class Delivery(IdMixin, TimestampMixin, OrgMixin, DemoMixin, Base):
    __tablename__ = "deliveries"
    __table_args__ = (
        UniqueConstraint("organization_id", "reference"),
        Index("ix_delivery_org_status", "organization_id", "status"),
        Index("ix_delivery_org_deadline", "organization_id", "deadline"),
        in_list("status", DELIVERY_STATUS, "ck_delivery_status"),
    )
    reference: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    description: Mapped[str | None] = mapped_column(Text)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    pickup_address: Mapped[str] = mapped_column(String(255))
    pickup_lat: Mapped[float | None] = mapped_column(Float)
    pickup_lng: Mapped[float | None] = mapped_column(Float)
    dest_address: Mapped[str] = mapped_column(String(255))
    dest_lat: Mapped[float | None] = mapped_column(Float)
    dest_lng: Mapped[float | None] = mapped_column(Float)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    customer_name: Mapped[str | None] = mapped_column(String(160))
    customer_phone: Mapped[str | None] = mapped_column(String(40))
    customer_email: Mapped[str | None] = mapped_column(String(254))
    proof_url: Mapped[str | None] = mapped_column(String(500))
    vehicle_id: Mapped[uuid.UUID | None] = fk("vehicles", True, "SET NULL")
    driver_id: Mapped[uuid.UUID | None] = fk("drivers", True, "SET NULL")
    route_id: Mapped[uuid.UUID | None] = fk("routes", True, "SET NULL")


class Stop(IdMixin, OrgMixin, Base):
    __tablename__ = "stops"
    __table_args__ = (UniqueConstraint("route_id", "sequence"),)
    route_id: Mapped[uuid.UUID] = fk("routes", False, "CASCADE")
    sequence: Mapped[int]
    address: Mapped[str] = mapped_column(String(255))
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    eta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_id: Mapped[uuid.UUID | None] = fk("deliveries", True, "SET NULL")


class FuelTransaction(IdMixin, OrgMixin, DemoMixin, Base):
    __tablename__ = "fuel_transactions"
    __table_args__ = (Index("ix_fuel_vehicle_time", "vehicle_id", "occurred_at"),)
    vehicle_id: Mapped[uuid.UUID] = fk("vehicles", False, "CASCADE")
    driver_id: Mapped[uuid.UUID | None] = fk("drivers", True, "SET NULL")
    liters: Mapped[float] = mapped_column(Float)
    cost: Mapped[float] = mapped_column(Numeric(12, 2))
    odometer_km: Mapped[int | None]
    station: Mapped[str | None] = mapped_column(String(120))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MaintenanceRecord(IdMixin, TimestampMixin, OrgMixin, DemoMixin, Base):
    __tablename__ = "maintenance_records"
    __table_args__ = (in_list("status", MAINT_STATUS, "ck_maint_status"), in_list("kind", ["preventive", "repair", "inspection"], "ck_maint_kind"))
    vehicle_id: Mapped[uuid.UUID] = fk("vehicles", False, "CASCADE")
    kind: Mapped[str] = mapped_column(String(16), default="preventive")
    description: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), default="scheduled")
    cost: Mapped[float | None] = mapped_column(Numeric(12, 2))
    odometer_km: Mapped[int | None]
    scheduled_for: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Inspection(IdMixin, OrgMixin, DemoMixin, Base):
    __tablename__ = "inspections"
    vehicle_id: Mapped[uuid.UUID] = fk("vehicles", False, "CASCADE")
    inspector_id: Mapped[uuid.UUID | None] = fk("users", True, "SET NULL")
    passed: Mapped[bool]
    notes: Mapped[str | None] = mapped_column(Text)
    inspected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class VehicleLocation(IdMixin, OrgMixin, Base):
    __tablename__ = "vehicle_locations"
    __table_args__ = (Index("ix_location_vehicle_time", "vehicle_id", "recorded_at"),)
    vehicle_id: Mapped[uuid.UUID] = fk("vehicles", False, "CASCADE")
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    speed_kph: Mapped[float | None] = mapped_column(Float)
    heading: Mapped[float | None] = mapped_column(Float)
    is_simulated: Mapped[bool] = mapped_column(default=True)  # real GPS feeds set this to False
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Notification(IdMixin, OrgMixin, Base):
    """An alert shown in the notification center.

    user_id NULL means "everyone in the organization". Read state is per user (see
    NotificationRead), so one person reading an alert does not hide it from a colleague.
    `is_read` is kept from Phase 4 and is no longer used. Smart alerts carry a dedupe_key
    so the same condition is only ever raised once per organization.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notification_org_read", "organization_id", "is_read"),
        Index("ix_notification_org_created", "organization_id", "created_at"),
        UniqueConstraint("organization_id", "dedupe_key", name="uq_notification_dedupe"),
        in_list("severity", SEVERITY, "ck_notification_severity"),
    )
    user_id: Mapped[uuid.UUID | None] = fk("users", True, "CASCADE")
    severity: Mapped[str] = mapped_column(String(10), default="info")
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(default=False)
    kind: Mapped[str | None] = mapped_column(String(32))
    link: Mapped[str | None] = mapped_column(String(255))
    dedupe_key: Mapped[str | None] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class NotificationRead(Base):
    __tablename__ = "notification_reads"
    notification_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("notifications.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AIInsight(IdMixin, OrgMixin, DemoMixin, Base):
    __tablename__ = "ai_insights"
    kind: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    data: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Geofence(IdMixin, TimestampMixin, OrgMixin, Base):
    """A circular zone. Vehicles entering or leaving it raise an event."""

    __tablename__ = "geofences"
    __table_args__ = (UniqueConstraint("organization_id", "name"),)
    name: Mapped[str] = mapped_column(String(120))
    center_lat: Mapped[float] = mapped_column(Float)
    center_lng: Mapped[float] = mapped_column(Float)
    radius_m: Mapped[float] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
