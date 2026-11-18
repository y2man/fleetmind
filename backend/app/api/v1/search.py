"""Global search across vehicles, drivers and deliveries (only what the caller may read)."""
from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.rbac import permissions_for
from app.models import Delivery, Driver, User, Vehicle
from app.schemas.analytics import SearchHit, SearchOut

router = APIRouter(tags=["search"])
search_limit = rate_limit("search", 120, 60)  # per IP, in memory: the command palette searches as you type
PER_TYPE = 5


def _like(s: str) -> str:
    esc = s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{esc.lower()}%"


def _match(model, cols: list[str], like: str):
    return or_(*[func.lower(getattr(model, c)).like(like, escape="\\") for c in cols])


@router.get("/search", response_model=SearchOut, dependencies=[Depends(search_limit)])
def search(q: str = Query(..., min_length=2, max_length=100), user: User = Depends(require("analytics:read")), db: Session = Depends(get_db)):
    term = q.strip()
    have = permissions_for(user.role_name)
    org = user.organization_id
    like = _like(term)
    out: list[SearchHit] = []
    if len(term) < 2:
        return SearchOut(query=term, results=out)

    def link(path: str) -> str:
        return f"/app/{path}?q={quote(term)}"

    if "vehicles:read" in have:
        for v in db.scalars(select(Vehicle).where(Vehicle.organization_id == org, _match(Vehicle, ["registration", "manufacturer", "model"], like)).order_by(Vehicle.registration).limit(PER_TYPE)):
            out.append(SearchHit(type="vehicle", id=v.id, title=v.registration, subtitle=f"{v.manufacturer} {v.model} · {v.status}", url=link("fleet")))
    if "drivers:read" in have:
        for d in db.scalars(select(Driver).where(Driver.organization_id == org, _match(Driver, ["full_name", "license_number", "email"], like)).order_by(Driver.full_name).limit(PER_TYPE)):
            out.append(SearchHit(type="driver", id=d.id, title=d.full_name, subtitle=f"License {d.license_number} · {d.availability.replace('_', ' ')}", url=link("drivers")))
    if "deliveries:read" in have:
        for d in db.scalars(select(Delivery).where(Delivery.organization_id == org, _match(Delivery, ["reference", "pickup_address", "dest_address"], like)).order_by(Delivery.created_at.desc()).limit(PER_TYPE)):
            out.append(SearchHit(type="delivery", id=d.id, title=d.reference, subtitle=f"{d.status.replace('_', ' ')} · {d.dest_address}", url=link("deliveries")))
    return SearchOut(query=term, results=out)
