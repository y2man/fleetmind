"""Response schemas for analytics, notifications and search."""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DateRange(BaseModel):
    start: str
    end: str
    days: int = 0
    bucket_days: int = 1


class AnalyticsKpi(BaseModel):
    key: str
    label: str
    value: float | None
    previous: float | None
    suffix: str
    decimals: int
    good: Literal["up", "down", "neutral"]
    change_pct: float | None


class AnalyticsPoint(BaseModel):
    label: str
    start: str
    created: int
    delivered: int
    late: int
    fuel_cost: float
    liters: float
    maintenance_cost: float


class StatusCount(BaseModel):
    status: str
    count: int


class FuelVehicleRow(BaseModel):
    vehicle: str
    liters: float
    cost: float
    fills: int
    cost_per_liter: float | None


class DriverRow(BaseModel):
    driver: str
    delivered: int
    judged: int
    on_time: int
    late: int
    on_time_rate_pct: float | None


class MaintenanceKindRow(BaseModel):
    kind: str
    count: int
    cost: float


class AnalyticsOut(BaseModel):
    range: DateRange
    previous_range: DateRange
    kpis: list[AnalyticsKpi]
    series: list[AnalyticsPoint]
    delivery_status: list[StatusCount]
    fuel_by_vehicle: list[FuelVehicleRow]
    drivers: list[DriverRow]
    maintenance_by_kind: list[MaintenanceKindRow]
    vehicles_by_status: dict[str, int]
    notes: list[str]
    has_data: bool


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    severity: Literal["info", "warning", "critical"]
    title: str
    body: str | None = None
    kind: str | None = None
    link: str | None = None
    created_at: datetime
    is_read: bool = False


class NotificationList(BaseModel):
    items: list[NotificationOut]
    unread_count: int


class RefreshOut(BaseModel):
    created: int
    unread_count: int


class SearchHit(BaseModel):
    type: Literal["vehicle", "driver", "delivery"]
    id: uuid.UUID
    title: str
    subtitle: str | None = None
    url: str


class SearchOut(BaseModel):
    query: str
    results: list[SearchHit]
