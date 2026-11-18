"""Fleet, drivers, deliveries, fuel and maintenance: all built on the generic CRUD router."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter

from app.api.v1.crud import build_router
from app.models import Delivery, Driver, FuelTransaction, MaintenanceRecord, Vehicle
from app.schemas import fleet as s

router = APIRouter()


def _delivery_prepare(values: dict, row) -> None:
    if row is None and not values.get("reference"):
        values["reference"] = "D-" + uuid.uuid4().hex[:8].upper()
    # Mark the delivery time when a delivery is completed without an explicit time.
    if values.get("status") == "delivered" and not values.get("delivered_at") and not (row and row.delivered_at):
        values["delivered_at"] = datetime.now(timezone.utc)
    # Moving a delivery back out of "delivered" clears the delivery time.
    if "status" in values and values["status"] != "delivered" and row is not None and row.delivered_at:
        values["delivered_at"] = None


def _maintenance_prepare(values: dict, row) -> None:
    if values.get("status") == "completed" and not values.get("completed_at") and not (row and row.completed_at):
        values["completed_at"] = datetime.now(timezone.utc)


router.include_router(build_router(
    path="vehicles", entity="vehicle", perm="vehicles", model=Vehicle,
    create_schema=s.VehicleCreate, update_schema=s.VehicleUpdate, out_schema=s.VehicleOut,
    search=["registration", "manufacturer", "model"],
    sort_fields=["registration", "manufacturer", "model", "year", "status", "fuel_type", "mileage_km", "created_at"],
    default_sort="created_at", filters=["status", "fuel_type", "driver_id"],
    label=lambda r: r.registration, option_label=lambda r: f"{r.registration} · {r.manufacturer} {r.model}",
))
router.include_router(build_router(
    path="drivers", entity="driver", perm="drivers", model=Driver,
    create_schema=s.DriverCreate, update_schema=s.DriverUpdate, out_schema=s.DriverOut,
    search=["full_name", "license_number", "email"],
    sort_fields=["full_name", "license_number", "license_expiry", "availability", "safety_score", "created_at"],
    default_sort="created_at", filters=["availability"],
    label=lambda r: r.full_name, option_label=lambda r: r.full_name,
))
router.include_router(build_router(
    path="deliveries", entity="delivery", perm="deliveries", model=Delivery,
    create_schema=s.DeliveryCreate, update_schema=s.DeliveryUpdate, out_schema=s.DeliveryOut,
    search=["reference", "pickup_address", "dest_address", "customer_name"],
    sort_fields=["reference", "status", "deadline", "weight_kg", "delivered_at", "created_at"],
    default_sort="created_at", filters=["status", "vehicle_id", "driver_id"],
    label=lambda r: r.reference, prepare=_delivery_prepare,
))
router.include_router(build_router(
    path="fuel", entity="fuel_transaction", perm="fuel", model=FuelTransaction,
    create_schema=s.FuelCreate, update_schema=s.FuelUpdate, out_schema=s.FuelOut,
    search=["station"],
    sort_fields=["occurred_at", "liters", "cost", "odometer_km"],
    default_sort="occurred_at", filters=["vehicle_id", "driver_id"],
    label=lambda r: f"{r.liters:g} L",
))
router.include_router(build_router(
    path="maintenance", entity="maintenance", perm="maintenance", model=MaintenanceRecord,
    create_schema=s.MaintenanceCreate, update_schema=s.MaintenanceUpdate, out_schema=s.MaintenanceOut,
    search=["description"],
    sort_fields=["scheduled_for", "status", "kind", "cost", "created_at"],
    default_sort="scheduled_for", filters=["status", "kind", "vehicle_id"],
    label=lambda r: r.description[:60],
    prepare=_maintenance_prepare,
))
