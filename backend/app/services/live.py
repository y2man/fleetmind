"""One simulation step for one organization: move vehicles, store positions, detect geofence events.

All positions here are SIMULATED and labeled so. A real GPS integration would feed
the same Vehicle.last_lat / VehicleLocation rows with is_simulated=False.
"""
from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Driver, Geofence, Notification, Vehicle, VehicleLocation
from app.schemas.tracking import LivePosition
from app.services import audit
from app.services.simulation import Mover, inside, new_mover, step

SAVE_EVERY_TICKS = 5  # store a history point every N ticks
PRUNE_EVERY_TICKS = 60
KEEP_HISTORY = timedelta(hours=1)


@dataclass
class OrgState:
    movers: dict[uuid.UUID, Mover] = field(default_factory=dict)
    inside: dict[tuple[uuid.UUID, uuid.UUID], bool] = field(default_factory=dict)
    rng: random.Random = field(default_factory=random.Random)
    ticks: int = 0


def run_tick(db: Session, org_id: uuid.UUID, state: OrgState, *, advance: bool, dt: float, boost: float) -> tuple[list[dict], list[dict]]:
    """Returns (positions, geofence_events). With advance=False vehicles are only placed, not moved."""
    vehicles = list(db.scalars(select(Vehicle).where(Vehicle.organization_id == org_id, Vehicle.status != "retired").order_by(Vehicle.registration)))
    geofences = list(db.scalars(select(Geofence).where(Geofence.organization_id == org_id, Geofence.is_active.is_(True))))
    drivers = {d.id: d.full_name for d in db.scalars(select(Driver).where(Driver.organization_id == org_id))}
    live_ids = {v.id for v in vehicles}
    if live_ids:
        real_locations = db.scalars(
            select(VehicleLocation)
            .where(
                VehicleLocation.organization_id == org_id,
                VehicleLocation.vehicle_id.in_(live_ids),
                VehicleLocation.is_simulated.is_(False),
            )
            .order_by(VehicleLocation.recorded_at.desc(), VehicleLocation.id.desc())
        )
        real_position_by_vehicle = {}
        for location in real_locations:
            real_position_by_vehicle.setdefault(location.vehicle_id, location)
    else:
        real_position_by_vehicle = {}
    for gone in [k for k in state.movers if k not in live_ids]:
        del state.movers[gone]

    now = datetime.now(timezone.utc)
    if advance:
        state.ticks += 1
    save_point = advance and state.ticks % SAVE_EVERY_TICKS == 0
    positions: list[dict] = []
    events: list[dict] = []
    for v in vehicles:
        real_position = real_position_by_vehicle.get(v.id)
        if real_position is not None:
            lat, lng = real_position.lat, real_position.lng
            speed = real_position.speed_kph
            heading = real_position.heading
            simulated = False
            # Keep the vehicle snapshot synchronized with the latest real GPS sample.
            v.last_lat, v.last_lng = lat, lng
        else:
            m = state.movers.get(v.id)
            if m is None:
                at = (v.last_lat, v.last_lng) if v.last_lat is not None and v.last_lng is not None else None
                m = state.movers[v.id] = new_mover(state.rng, at=at)
            moving = v.status == "active"
            if advance and moving:
                step(m, dt, state.rng, boost=boost)
            speed = round(m.speed_kph, 1) if moving else 0.0
            heading = round(m.heading, 1)
            lat, lng = round(m.lat, 6), round(m.lng, 6)
            simulated = True
            v.last_lat, v.last_lng = lat, lng
            if save_point and moving:
                db.add(VehicleLocation(organization_id=org_id, vehicle_id=v.id, lat=lat, lng=lng, speed_kph=speed, heading=heading, is_simulated=True, recorded_at=now))
        if advance:
            for g in geofences:
                key, now_in = (v.id, g.id), inside(lat, lng, g.center_lat, g.center_lng, g.radius_m)
                was = state.inside.get(key)
                state.inside[key] = now_in
                if was is None or was == now_in:  # first sighting is silent; only changes raise events
                    continue
                kind = "enter" if now_in else "exit"
                verb = "entered" if now_in else "left"
                events.append({"event": kind, "vehicle_id": str(v.id), "registration": v.registration, "geofence": g.name, "at": now.isoformat(), "simulated": simulated})
                body = "Simulated GPS position (demo)." if simulated else "Vehicle GPS position."
                db.add(Notification(organization_id=org_id, severity="info", title=f"{v.registration} {verb} {g.name}", body=body))
                audit.record(db, f"geofence.{'entered' if now_in else 'exited'}", org_id=org_id, entity_type="geofence", entity_id=str(g.id), detail={"vehicle_id": str(v.id), "registration": v.registration, "geofence": g.name, "simulated": simulated})
        positions.append(LivePosition(
            vehicle_id=v.id, registration=v.registration, label=f"{v.manufacturer} {v.model}", status=v.status,
            driver_label=drivers.get(v.driver_id), lat=lat, lng=lng, speed_kph=speed, heading=heading, simulated=simulated,
        ).model_dump(mode="json"))
    if advance and state.ticks % PRUNE_EVERY_TICKS == 0:
        db.execute(delete(VehicleLocation).where(VehicleLocation.organization_id == org_id, VehicleLocation.is_simulated.is_(True), VehicleLocation.recorded_at < now - KEEP_HISTORY))
    db.commit()
    return positions, events
