"""Request/response schemas for the Phase 5 core modules.

Create and update schemas share the same constrained types (aliases below) so
both enforce the same limits. Update schemas make every field optional.
"""
import uuid
from datetime import date, datetime
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

Str16 = Annotated[str, Field(min_length=1, max_length=16)]
Str32 = Annotated[str, Field(min_length=1, max_length=32)]
Str64 = Annotated[str, Field(min_length=1, max_length=64)]
Str80 = Annotated[str, Field(min_length=1, max_length=80)]
Str120 = Annotated[str, Field(min_length=1, max_length=120)]
Str160 = Annotated[str, Field(min_length=1, max_length=160)]
Str255 = Annotated[str, Field(min_length=1, max_length=255)]
Text = Annotated[str, Field(max_length=2000)]
Phone = Annotated[str, Field(max_length=40)]
Email = Annotated[str, Field(max_length=254)]
Lat = Annotated[float, Field(ge=-90, le=90)]
Lng = Annotated[float, Field(ge=-180, le=180)]

VehicleStatus = Literal["active", "idle", "maintenance", "retired"]
FuelType = Literal["diesel", "petrol", "electric", "hybrid", "cng"]
DriverStatus = Literal["available", "on_duty", "off_duty", "on_leave"]
DeliveryStatus = Literal["pending", "assigned", "in_transit", "delivered", "delayed", "cancelled"]
MaintStatus = Literal["scheduled", "in_progress", "completed", "cancelled"]
MaintKind = Literal["preventive", "repair", "inspection"]


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class Option(BaseModel):
    id: uuid.UUID
    label: str


class _Base(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime | None = None


# ---------------------------------------------------------------- vehicles
class VehicleCreate(_Base):
    registration: Str32
    manufacturer: Str80
    model: Str80
    year: int | None = Field(default=None, ge=1950, le=2100)
    fuel_type: FuelType = "diesel"
    status: VehicleStatus = "idle"
    mileage_km: int = Field(default=0, ge=0, le=10_000_000)
    capacity_kg: int | None = Field(default=None, ge=0, le=1_000_000)
    driver_id: uuid.UUID | None = None
    insurance_expiry: date | None = None
    registration_expiry: date | None = None


class VehicleUpdate(_Base):
    registration: Str32 | None = None
    manufacturer: Str80 | None = None
    model: Str80 | None = None
    year: int | None = Field(default=None, ge=1950, le=2100)
    fuel_type: FuelType | None = None
    status: VehicleStatus | None = None
    mileage_km: int | None = Field(default=None, ge=0, le=10_000_000)
    capacity_kg: int | None = Field(default=None, ge=0, le=1_000_000)
    driver_id: uuid.UUID | None = None
    insurance_expiry: date | None = None
    registration_expiry: date | None = None


class VehicleOut(_Out):
    registration: str
    manufacturer: str
    model: str
    year: int | None
    fuel_type: str
    status: str
    mileage_km: int
    capacity_kg: int | None
    driver_id: uuid.UUID | None
    driver_label: str | None = None
    insurance_expiry: date | None
    registration_expiry: date | None
    is_demo: bool = False


# ----------------------------------------------------------------- drivers
class DriverCreate(_Base):
    full_name: Str160
    email: Email | None = None
    phone: Phone | None = None
    license_number: Str64
    license_expiry: date | None = None
    availability: DriverStatus = "available"
    safety_score: float | None = Field(default=None, ge=0, le=100)


class DriverUpdate(_Base):
    full_name: Str160 | None = None
    email: Email | None = None
    phone: Phone | None = None
    license_number: Str64 | None = None
    license_expiry: date | None = None
    availability: DriverStatus | None = None
    safety_score: float | None = Field(default=None, ge=0, le=100)


class DriverOut(_Out):
    full_name: str
    email: str | None
    phone: str | None
    license_number: str
    license_expiry: date | None
    availability: str
    safety_score: float | None
    is_demo: bool = False


# -------------------------------------------------------------- deliveries
class DeliveryCreate(_Base):
    reference: Str32 | None = None  # generated when omitted
    status: DeliveryStatus = "pending"
    description: Text | None = None
    weight_kg: float | None = Field(default=None, ge=0, le=1_000_000)
    pickup_address: Str255
    pickup_lat: Lat | None = None
    pickup_lng: Lng | None = None
    dest_address: Str255
    dest_lat: Lat | None = None
    dest_lng: Lng | None = None
    deadline: datetime | None = None
    customer_name: Str160 | None = None
    customer_phone: Phone | None = None
    customer_email: Email | None = None
    vehicle_id: uuid.UUID | None = None
    driver_id: uuid.UUID | None = None


class DeliveryUpdate(_Base):
    reference: Str32 | None = None
    status: DeliveryStatus | None = None
    description: Text | None = None
    weight_kg: float | None = Field(default=None, ge=0, le=1_000_000)
    pickup_address: Str255 | None = None
    pickup_lat: Lat | None = None
    pickup_lng: Lng | None = None
    dest_address: Str255 | None = None
    dest_lat: Lat | None = None
    dest_lng: Lng | None = None
    deadline: datetime | None = None
    delivered_at: datetime | None = None
    customer_name: Str160 | None = None
    customer_phone: Phone | None = None
    customer_email: Email | None = None
    vehicle_id: uuid.UUID | None = None
    driver_id: uuid.UUID | None = None


class DeliveryOut(_Out):
    reference: str
    status: str
    description: str | None
    weight_kg: float | None
    pickup_address: str
    dest_address: str
    pickup_lat: float | None
    pickup_lng: float | None
    dest_lat: float | None
    dest_lng: float | None
    deadline: datetime | None
    delivered_at: datetime | None
    customer_name: str | None
    customer_phone: str | None
    customer_email: str | None
    vehicle_id: uuid.UUID | None
    vehicle_label: str | None = None
    driver_id: uuid.UUID | None
    driver_label: str | None = None
    is_demo: bool = False


# -------------------------------------------------------------------- fuel
class FuelCreate(_Base):
    vehicle_id: uuid.UUID
    driver_id: uuid.UUID | None = None
    liters: float = Field(gt=0, le=10_000)
    cost: float = Field(ge=0, le=10_000_000)
    odometer_km: int | None = Field(default=None, ge=0, le=10_000_000)
    station: Str120 | None = None
    occurred_at: datetime | None = None


class FuelUpdate(_Base):
    vehicle_id: uuid.UUID | None = None
    driver_id: uuid.UUID | None = None
    liters: float | None = Field(default=None, gt=0, le=10_000)
    cost: float | None = Field(default=None, ge=0, le=10_000_000)
    odometer_km: int | None = Field(default=None, ge=0, le=10_000_000)
    station: Str120 | None = None
    occurred_at: datetime | None = None


class FuelOut(_Out):
    vehicle_id: uuid.UUID
    vehicle_label: str | None = None
    driver_id: uuid.UUID | None
    driver_label: str | None = None
    liters: float
    cost: float
    odometer_km: int | None
    station: str | None
    occurred_at: datetime
    is_demo: bool = False


# ------------------------------------------------------------- maintenance
class MaintenanceCreate(_Base):
    vehicle_id: uuid.UUID
    kind: MaintKind = "preventive"
    description: Str255
    status: MaintStatus = "scheduled"
    cost: float | None = Field(default=None, ge=0, le=10_000_000)
    odometer_km: int | None = Field(default=None, ge=0, le=10_000_000)
    scheduled_for: date | None = None
    completed_at: datetime | None = None


class MaintenanceUpdate(_Base):
    vehicle_id: uuid.UUID | None = None
    kind: MaintKind | None = None
    description: Str255 | None = None
    status: MaintStatus | None = None
    cost: float | None = Field(default=None, ge=0, le=10_000_000)
    odometer_km: int | None = Field(default=None, ge=0, le=10_000_000)
    scheduled_for: date | None = None
    completed_at: datetime | None = None


class MaintenanceOut(_Out):
    vehicle_id: uuid.UUID
    vehicle_label: str | None = None
    kind: str
    description: str
    status: str
    cost: float | None
    odometer_km: int | None
    scheduled_for: date | None
    completed_at: datetime | None
    is_demo: bool = False


# --------------------------------------------------------------- dashboard
class Kpi(BaseModel):
    key: str
    label: str
    value: float | None
    suffix: str = ""
    decimals: int = 0


class SeriesPoint(BaseModel):
    label: str
    completed: int = 0
    delayed: int = 0
    cost: float = 0


class Alert(BaseModel):
    severity: Literal["critical", "warning"]
    text: str


class ActivityItem(BaseModel):
    text: str
    at: datetime


class UpcomingMaintenance(BaseModel):
    vehicle: str
    task: str
    due: date | None
    overdue: bool


class DashboardOut(BaseModel):
    days: int
    kpis: list[Kpi]
    deliveries: list[SeriesPoint]
    fuel: list[SeriesPoint]
    vehicle_status: dict[str, int]
    alerts: list[Alert]
    activity: list[ActivityItem]
    maintenance: list[UpcomingMaintenance]
    has_data: bool
