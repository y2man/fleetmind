"""Route planning (multi-stop, ordered by a nearest-neighbour + 2-opt heuristic) and geofences.

Same security properties as the Phase 5 modules: every query is limited to the caller's
organization, vehicle/driver/delivery references must belong to it, writes are audited.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import client_ip, require
from app.api.v1.crud import build_router, enrich
from app.core.config import get_settings
from app.core.database import get_db
from app.models import Delivery, Driver, Geofence, Route, Stop, User, Vehicle
from app.schemas.fleet import Page
from app.schemas.tracking import (
    FleetPlanIn, FleetPlanOut, GeofenceCreate, GeofenceOut, GeofenceUpdate, PlanIn, PlanOut, RouteCreate,
    RouteOut, RouteUpdate, StopIn, StopOut,
)
from app.services import audit
from app.services.routing import (
    Assumptions, RoutingProviderError, osrm_matrices, plan as make_plan, plan_fleet_ortools, plan_osrm,
)

router = APIRouter()

router.include_router(build_router(
    path="geofences", entity="geofence", perm="routes", model=Geofence,
    create_schema=GeofenceCreate, update_schema=GeofenceUpdate, out_schema=GeofenceOut,
    search=["name"], sort_fields=["name", "radius_m", "created_at"], default_sort="created_at",
    label=lambda r: r.name,
))

routes = APIRouter(prefix="/routes", tags=["routes"])
read, write = require("routes:read"), require("routes:write")


def _check_refs(db: Session, user: User, vehicle_id, driver_id, stops: list[StopIn] | None = None) -> None:
    org = user.organization_id
    if vehicle_id and not db.scalar(select(Vehicle.id).where(Vehicle.id == vehicle_id, Vehicle.organization_id == org)):
        raise HTTPException(422, "Unknown vehicle")
    if driver_id and not db.scalar(select(Driver.id).where(Driver.id == driver_id, Driver.organization_id == org)):
        raise HTTPException(422, "Unknown driver")
    ids = {s.delivery_id for s in (stops or []) if s.delivery_id}
    if ids:
        found = set(db.scalars(select(Delivery.id).where(Delivery.organization_id == org, Delivery.id.in_(ids))))
        if found != ids:
            raise HTTPException(422, "Unknown delivery")


def _plan(body: PlanIn, optimize: bool = True) -> tuple[dict, list[StopIn]]:
    points = [(s.lat, s.lng) for s in body.stops]
    a = Assumptions(**body.assumptions.model_dump()) if body.assumptions else Assumptions()
    settings = get_settings()
    if settings.osrm_base_url:
        try:
            result = plan_osrm(
                points, a, settings.osrm_base_url, settings.osrm_profile,
                settings.osrm_timeout_seconds,
            )
        except RoutingProviderError as exc:
            raise HTTPException(503, str(exc)) from exc
    else:
        result = make_plan(points, a)
    if not optimize:
        result["order"] = list(range(len(points)))
        result["optimized"] = result["original"]
        result["saved"] = {"distance_km": 0.0, "duration_min": 0, "fuel_l": 0.0}
        result["saved_percent"] = 0.0
    return result, [body.stops[i] for i in result["order"]]


def _out(db: Session, org_id: uuid.UUID, route: Route, with_stops: bool) -> RouteOut:
    enrich(db, org_id, Route, [route])
    stops = list(db.scalars(select(Stop).where(Stop.route_id == route.id, Stop.organization_id == org_id).order_by(Stop.sequence)))
    out = RouteOut.model_validate(route)
    out.stop_count = len(stops)
    out.stops = [StopOut.model_validate(s) for s in stops] if with_stops else []
    return out


@routes.post("/plan", response_model=PlanOut)
def plan_route(body: PlanIn, user: User = Depends(read), db: Session = Depends(get_db)):
    """Preview only: nothing is saved."""
    _check_refs(db, user, None, None, body.stops)
    result, ordered = _plan(body)
    return PlanOut(**result, stops=ordered)


@routes.post("/plan-fleet", response_model=FleetPlanOut)
def plan_fleet(body: FleetPlanIn, user: User = Depends(read), db: Session = Depends(get_db)):
    vehicle_ids = [vehicle.vehicle_id for vehicle in body.vehicles]
    if len(set(vehicle_ids)) != len(vehicle_ids):
        raise HTTPException(422, "Each vehicle can only be included once")
    vehicles_by_id = {
        vehicle.id: vehicle
        for vehicle in db.scalars(select(Vehicle).where(
            Vehicle.organization_id == user.organization_id,
            Vehicle.id.in_(vehicle_ids),
        ))
    }
    if len(vehicles_by_id) != len(vehicle_ids):
        raise HTTPException(422, "Unknown vehicle")
    capacities = []
    for spec in body.vehicles:
        vehicle = vehicles_by_id[spec.vehicle_id]
        if vehicle.status == "retired" or vehicle.capacity_kg is None:
            raise HTTPException(422, "Every planning vehicle must be non-retired and have a configured capacity")
        capacities.append(vehicle.capacity_kg)

    driver_ids = [vehicle.driver_id for vehicle in body.vehicles if vehicle.driver_id]
    if len(set(driver_ids)) != len(driver_ids):
        raise HTTPException(422, "A driver cannot be assigned to multiple vehicles")
    if driver_ids:
        available_drivers = set(db.scalars(select(Driver.id).where(
            Driver.organization_id == user.organization_id,
            Driver.id.in_(driver_ids),
            Driver.availability == "available",
        )))
        if available_drivers != set(driver_ids):
            raise HTTPException(422, "Unknown or unavailable driver")

    assumptions = Assumptions(**body.assumptions.model_dump()) if body.assumptions else Assumptions()
    vehicle_data = [vehicle.model_dump(mode="json") for vehicle in body.vehicles]
    stop_data = [stop.model_dump() for stop in body.stops]
    matrix_points = [(vehicle.start_lat, vehicle.start_lng) for vehicle in body.vehicles]
    matrix_points.extend((stop.lat, stop.lng) for stop in body.stops)
    distance_matrix = duration_matrix = None
    settings = get_settings()
    routing_provider = "estimate"
    if settings.osrm_base_url:
        try:
            distance_matrix, duration_matrix = osrm_matrices(
                matrix_points, settings.osrm_base_url, settings.osrm_profile,
                settings.osrm_timeout_seconds,
            )
        except RoutingProviderError as exc:
            raise HTTPException(503, str(exc)) from exc
        routing_provider = "OSRM"
    try:
        result = plan_fleet_ortools(
            stop_data,
            vehicle_data,
            capacities,
            assumptions,
            distance_matrix,
            duration_matrix,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    result["routing_provider"] = routing_provider
    return FleetPlanOut(**result)


@routes.get("", response_model=Page[RouteOut])
def list_routes(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user: User = Depends(read), db: Session = Depends(get_db)):
    base = select(Route).where(Route.organization_id == user.organization_id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = list(db.scalars(base.order_by(Route.created_at.desc(), Route.id).limit(page_size).offset((page - 1) * page_size)))
    enrich(db, user.organization_id, Route, rows)
    counts = dict(db.execute(select(Stop.route_id, func.count()).where(Stop.organization_id == user.organization_id, Stop.route_id.in_([r.id for r in rows])).group_by(Stop.route_id)).all()) if rows else {}
    items = []
    for r in rows:
        o = RouteOut.model_validate(r)
        o.stop_count = counts.get(r.id, 0)
        items.append(o)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def _get(db: Session, user: User, route_id: uuid.UUID) -> Route:
    row = db.scalar(select(Route).where(Route.id == route_id, Route.organization_id == user.organization_id))
    if not row:
        raise HTTPException(404, "Route not found")
    return row


@routes.get("/{route_id}", response_model=RouteOut)
def get_route(route_id: uuid.UUID, user: User = Depends(read), db: Session = Depends(get_db)):
    return _out(db, user.organization_id, _get(db, user, route_id), True)


@routes.post("", response_model=RouteOut, status_code=201)
def create_route(body: RouteCreate, request: Request, user: User = Depends(write), db: Session = Depends(get_db)):
    _check_refs(db, user, body.vehicle_id, body.driver_id, body.stops)
    result, ordered = _plan(body, body.optimize)
    route = Route(
        organization_id=user.organization_id, name=body.name, status="planned", vehicle_id=body.vehicle_id, driver_id=body.driver_id,
        total_distance_km=result["optimized"]["distance_km"], est_duration_min=result["optimized"]["duration_min"],
        optimization_notes={k: result[k] for k in ("original", "optimized", "saved", "saved_percent", "assumptions")} | {"optimized": body.optimize, "estimates": True},
    )
    db.add(route)
    db.flush()
    for i, s in enumerate(ordered, start=1):
        db.add(Stop(organization_id=user.organization_id, route_id=route.id, sequence=i, address=s.address, lat=s.lat, lng=s.lng, delivery_id=s.delivery_id))
        if s.delivery_id:
            d = db.get(Delivery, s.delivery_id)
            d.route_id = route.id
    audit.record(db, "route.created", user=user, ip=client_ip(request), entity_type="route", entity_id=str(route.id), detail={"label": route.name, "stops": len(ordered)})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Could not save the route")
    return _out(db, user.organization_id, route, True)


@routes.patch("/{route_id}", response_model=RouteOut)
def update_route(route_id: uuid.UUID, body: RouteUpdate, request: Request, user: User = Depends(write), db: Session = Depends(get_db)):
    route = _get(db, user, route_id)
    values = body.model_dump(exclude_unset=True)
    for k in ("name", "status"):
        if k in values and values[k] is None:
            raise HTTPException(422, f"{k} cannot be empty")
    _check_refs(db, user, values.get("vehicle_id"), values.get("driver_id"))
    for k, v in values.items():
        setattr(route, k, v)
    audit.record(db, "route.updated", user=user, ip=client_ip(request), entity_type="route", entity_id=str(route.id), detail={"label": route.name, "fields": sorted(values)})
    db.commit()
    return _out(db, user.organization_id, route, True)


@routes.delete("/{route_id}", status_code=204)
def delete_route(route_id: uuid.UUID, request: Request, user: User = Depends(write), db: Session = Depends(get_db)):
    route = _get(db, user, route_id)
    audit.record(db, "route.deleted", user=user, ip=client_ip(request), entity_type="route", entity_id=str(route.id), detail={"label": route.name})
    db.delete(route)  # stops are removed by the database (ON DELETE CASCADE); deliveries are unlinked (SET NULL)
    db.commit()


router.include_router(routes)
