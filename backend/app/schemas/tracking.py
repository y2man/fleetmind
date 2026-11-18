"""Schemas for geofences, routes and live tracking (Phase 6)."""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.fleet import Lat, Lng, Str120, Str160, Str255, _Base, _Out

RouteStatus = Literal["draft", "planned", "in_progress", "completed"]


# ---------------------------------------------------------------- geofences
class GeofenceCreate(_Base):
    name: Str120
    center_lat: Lat
    center_lng: Lng
    radius_m: float = Field(gt=0, le=100_000)
    is_active: bool = True


class GeofenceUpdate(_Base):
    name: Str120 | None = None
    center_lat: Lat | None = None
    center_lng: Lng | None = None
    radius_m: float | None = Field(default=None, gt=0, le=100_000)
    is_active: bool | None = None


class GeofenceOut(_Out):
    name: str
    center_lat: float
    center_lng: float
    radius_m: float
    is_active: bool


# ------------------------------------------------------------------- routes
class StopIn(_Base):
    address: Str255
    lat: Lat
    lng: Lng
    delivery_id: uuid.UUID | None = None


class AssumptionsIn(_Base):
    road_factor: float = Field(default=1.3, ge=1, le=3)
    avg_speed_kph: float = Field(default=40, gt=5, le=120)
    stop_minutes: float = Field(default=10, ge=0, le=240)
    fuel_l_per_100km: float = Field(default=12, gt=0, le=100)


class PlanIn(_Base):
    stops: list[StopIn] = Field(min_length=2, max_length=25)  # the first stop is the start and stays first
    assumptions: AssumptionsIn | None = None


class FleetPlanningStopIn(_Base):
    address: Str255
    lat: Lat
    lng: Lng
    demand_kg: int = Field(ge=0, le=1_000_000)
    window_start_minute: int = Field(default=0, ge=0, le=2879)
    window_end_minute: int = Field(default=1440, ge=1, le=2880)
    service_minutes: int = Field(default=10, ge=0, le=240)

    @model_validator(mode="after")
    def valid_window(self):
        if self.window_end_minute <= self.window_start_minute:
            raise ValueError("window_end_minute must be after window_start_minute")
        return self


class FleetPlanningVehicleIn(_Base):
    vehicle_id: uuid.UUID
    driver_id: uuid.UUID | None = None
    start_lat: Lat
    start_lng: Lng
    shift_start_minute: int = Field(default=0, ge=0, le=2879)
    shift_end_minute: int = Field(default=1440, ge=1, le=2880)

    @model_validator(mode="after")
    def valid_shift(self):
        if self.shift_end_minute <= self.shift_start_minute:
            raise ValueError("shift_end_minute must be after shift_start_minute")
        return self


class FleetPlanIn(_Base):
    stops: list[FleetPlanningStopIn] = Field(min_length=1, max_length=50)
    vehicles: list[FleetPlanningVehicleIn] = Field(min_length=1, max_length=10)
    assumptions: AssumptionsIn | None = None


class FleetVehiclePlanOut(BaseModel):
    vehicle_id: uuid.UUID
    driver_id: uuid.UUID | None
    stop_indices: list[int]
    arrival_minutes: list[int]
    distance_km: float
    elapsed_minutes: int
    fuel_l: float


class FleetPlanOut(BaseModel):
    routes: list[FleetVehiclePlanOut]
    total_distance_km: float
    total_elapsed_minutes: int
    total_fuel_l: float
    routing_provider: str
    method: str = "Google OR-Tools capacitated vehicle routing with time windows"


class Estimate(BaseModel):
    distance_km: float
    duration_min: int
    fuel_l: float


class PlanOut(BaseModel):
    order: list[int]
    stops: list[StopIn]  # in the recommended order
    original: Estimate
    optimized: Estimate
    saved: Estimate
    saved_percent: float
    assumptions: dict
    method: str = "nearest-neighbour + 2-opt on straight-line distances"


class RouteCreate(PlanIn):
    name: Str160
    vehicle_id: uuid.UUID | None = None
    driver_id: uuid.UUID | None = None
    optimize: bool = True


class RouteUpdate(_Base):
    name: Str160 | None = None
    status: RouteStatus | None = None
    vehicle_id: uuid.UUID | None = None
    driver_id: uuid.UUID | None = None


class StopOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    sequence: int
    address: str
    lat: float | None
    lng: float | None
    delivery_id: uuid.UUID | None


class RouteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    status: str
    vehicle_id: uuid.UUID | None
    vehicle_label: str | None = None
    driver_id: uuid.UUID | None
    driver_label: str | None = None
    total_distance_km: float | None
    est_duration_min: int | None
    optimization_notes: dict | None
    created_at: datetime | None = None
    stop_count: int = 0
    stops: list[StopOut] = []


# ----------------------------------------------------------------- tracking
class LivePosition(BaseModel):
    vehicle_id: uuid.UUID
    registration: str
    label: str
    status: str
    driver_label: str | None = None
    lat: float
    lng: float
    speed_kph: float | None = None
    heading: float | None = None
    simulated: bool = True


class HistoryPoint(BaseModel):
    lat: float
    lng: float
    speed_kph: float | None
    recorded_at: datetime
    simulated: bool


class GeofenceEvent(BaseModel):
    event: Literal["enter", "exit"]
    vehicle_id: str | None
    registration: str | None
    geofence: str | None
    at: datetime
    simulated: bool = True
