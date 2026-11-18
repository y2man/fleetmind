"""Live tracking: WebSocket feed (simulated GPS), position snapshot, history and geofence events."""
import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require
from app.core.database import get_db, get_session_factory
from app.core.rbac import permissions_for
from app.core.security import decode_token
from app.models import AuditLog, Driver, User, Vehicle, VehicleLocation
from app.schemas.tracking import GeofenceEvent, HistoryPoint, LivePosition
from app.websocket.manager import hub

router = APIRouter(tags=["tracking"])
AUTH_TIMEOUT_S = 5


def _aware(dt):
    from datetime import timezone
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


@router.get("/tracking/vehicles", response_model=list[LivePosition])
def last_positions(user: User = Depends(require("vehicles:read")), db: Session = Depends(get_db)):
    """Last known position of each vehicle that has one (simulated until a real GPS feed exists)."""
    org = user.organization_id
    drivers = {d.id: d.full_name for d in db.scalars(select(Driver).where(Driver.organization_id == org))}
    vehicles = list(db.scalars(select(Vehicle).where(
        Vehicle.organization_id == org,
        Vehicle.last_lat.is_not(None),
        Vehicle.last_lng.is_not(None),
    ).order_by(Vehicle.registration)))
    if not vehicles:
        return []
    latest = (
        select(
            VehicleLocation.id.label("id"),
            func.row_number().over(
                partition_by=VehicleLocation.vehicle_id,
                order_by=(VehicleLocation.recorded_at.desc(), VehicleLocation.id.desc()),
            ).label("position"),
        )
        .where(
            VehicleLocation.organization_id == org,
            VehicleLocation.vehicle_id.in_([v.id for v in vehicles]),
            VehicleLocation.is_simulated.is_(False),
        )
        .subquery()
    )
    real_by_vehicle = {
        row.vehicle_id: row
        for row in db.scalars(
            select(VehicleLocation)
            .join(latest, latest.c.id == VehicleLocation.id)
            .where(latest.c.position == 1)
        )
    }
    return [
        LivePosition(
            vehicle_id=v.id, registration=v.registration, label=f"{v.manufacturer} {v.model}",
            status=v.status, driver_label=drivers.get(v.driver_id),
            lat=real_by_vehicle[v.id].lat if v.id in real_by_vehicle else v.last_lat,
            lng=real_by_vehicle[v.id].lng if v.id in real_by_vehicle else v.last_lng,
            speed_kph=real_by_vehicle[v.id].speed_kph if v.id in real_by_vehicle else None,
            heading=real_by_vehicle[v.id].heading if v.id in real_by_vehicle else None,
            simulated=v.id not in real_by_vehicle,
        )
        for v in vehicles
    ]


@router.get("/tracking/vehicles/{vehicle_id}/history", response_model=list[HistoryPoint])
def history(vehicle_id: uuid.UUID, limit: int = Query(60, ge=1, le=300), user: User = Depends(require("vehicles:read")), db: Session = Depends(get_db)):
    org = user.organization_id
    if not db.scalar(select(Vehicle.id).where(Vehicle.id == vehicle_id, Vehicle.organization_id == org)):
        raise HTTPException(404, "Vehicle not found")
    rows = list(db.scalars(select(VehicleLocation).where(VehicleLocation.organization_id == org, VehicleLocation.vehicle_id == vehicle_id).order_by(VehicleLocation.recorded_at.desc()).limit(limit)))
    return [HistoryPoint(lat=r.lat, lng=r.lng, speed_kph=r.speed_kph, recorded_at=_aware(r.recorded_at), simulated=r.is_simulated) for r in reversed(rows)]


@router.get("/tracking/events", response_model=list[GeofenceEvent])
def geofence_events(limit: int = Query(30, ge=1, le=100), user: User = Depends(require("vehicles:read")), db: Session = Depends(get_db)):
    rows = db.scalars(select(AuditLog).where(AuditLog.organization_id == user.organization_id, AuditLog.action.in_(("geofence.entered", "geofence.exited"))).order_by(AuditLog.created_at.desc()).limit(limit))
    out = []
    for r in rows:
        d = r.detail or {}
        out.append(GeofenceEvent(event="enter" if r.action.endswith("entered") else "exit", vehicle_id=d.get("vehicle_id"), registration=d.get("registration"), geofence=d.get("geofence"), at=_aware(r.created_at), simulated=bool(d.get("simulated", True))))
    return out


@router.websocket("/ws/tracking")
async def tracking_socket(ws: WebSocket, factory=Depends(get_session_factory)):
    """Protocol: connect, then send {"type":"auth","token":"<access token>"} within 5 seconds
    (the token is not put in the URL, so it stays out of server logs). The server answers with a
    snapshot, then sends positions every tick and geofence events as they happen."""
    await ws.accept()
    org_id = None
    try:
        msg = await asyncio.wait_for(ws.receive_json(), AUTH_TIMEOUT_S)
        user = await asyncio.to_thread(_authenticate, factory, msg)
        if user is None:
            await ws.close(code=4401)
            return
        org_id = user
        await hub.connect(ws, org_id, factory)
        while True:  # the client sends nothing else; this just detects disconnects
            await ws.receive_text()
    except (WebSocketDisconnect, asyncio.TimeoutError, ValueError, KeyError):
        pass
    finally:
        if org_id is not None:
            hub.disconnect(ws, org_id)
        try:
            await ws.close()
        except Exception:
            pass


def _authenticate(factory, msg) -> uuid.UUID | None:
    """Returns the organization id when the token is valid and the user may read vehicles."""
    if not isinstance(msg, dict) or msg.get("type") != "auth" or not isinstance(msg.get("token"), str):
        return None
    try:
        payload = decode_token(msg["token"], "access")
        with factory() as db:
            user = db.get(User, uuid.UUID(payload["sub"]))
            if not user or not user.is_active or str(user.organization_id) != payload.get("org"):
                return None
            if "vehicles:read" not in permissions_for(user.role_name):
                return None
            return user.organization_id
    except (ValueError, KeyError):
        return None
