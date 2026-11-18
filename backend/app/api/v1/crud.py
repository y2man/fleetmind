"""Generic, organization-scoped CRUD router used by the Phase 5 modules.

Security properties, enforced in one place so no module can forget them:
  * every query is filtered by the caller's organization_id (other orgs' ids look like 404)
  * read/write permissions are checked per resource through require()
  * foreign references (vehicle_id, driver_id) must belong to the same organization
  * every create/update/delete is written to the audit log

NOTE: this module deliberately does not use `from __future__ import annotations`,
because FastAPI needs the real (closure-defined) schema classes as annotations.
"""
import uuid
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import Uuid, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import client_ip, require
from app.core.database import get_db
from app.models import Driver, User, Vehicle
from app.schemas.fleet import Option, Page
from app.services import audit

REF_MODELS = {"vehicle_id": (Vehicle, "vehicle"), "driver_id": (Driver, "driver")}


def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def enrich(db: Session, org_id: uuid.UUID, model, rows: list) -> None:
    """Attach vehicle_label / driver_label to rows for display (one query per kind)."""
    if not rows:
        return
    if hasattr(model, "vehicle_id"):
        ids = {r.vehicle_id for r in rows if r.vehicle_id}
        labels = {}
        if ids:
            for v in db.scalars(select(Vehicle).where(Vehicle.organization_id == org_id, Vehicle.id.in_(ids))):
                labels[v.id] = f"{v.registration} · {v.manufacturer} {v.model}"
        for r in rows:
            r.vehicle_label = labels.get(r.vehicle_id)
    if hasattr(model, "driver_id"):
        ids = {r.driver_id for r in rows if r.driver_id}
        labels = {}
        if ids:
            for d in db.scalars(select(Driver).where(Driver.organization_id == org_id, Driver.id.in_(ids))):
                labels[d.id] = d.full_name
        for r in rows:
            r.driver_label = labels.get(r.driver_id)


def build_router(
    *,
    path: str,
    entity: str,
    perm: str,
    model,
    create_schema,
    update_schema,
    out_schema,
    search: list[str],
    sort_fields: list[str],
    default_sort: str,
    filters: list[str] = (),
    label: Callable[[Any], str],
    option_label: Callable[[Any], str] | None = None,
    prepare: Callable[[dict, Any], None] | None = None,
) -> APIRouter:
    router = APIRouter(prefix=f"/{path}", tags=[path])
    read = require(f"{perm}:read")
    write = require(f"{perm}:write")

    def get_row(db: Session, user: User, item_id: uuid.UUID):
        row = db.scalar(select(model).where(model.id == item_id, model.organization_id == user.organization_id))
        if not row:
            raise HTTPException(404, f"{entity.replace('_', ' ').capitalize()} not found")
        return row

    def check_refs(db: Session, user: User, values: dict) -> None:
        for field, (ref_model, name) in REF_MODELS.items():
            val = values.get(field)
            if val is None or not hasattr(model, field):
                continue
            ok = db.scalar(select(ref_model.id).where(ref_model.id == val, ref_model.organization_id == user.organization_id))
            if not ok:
                raise HTTPException(422, f"Unknown {name}")

    def save(db: Session) -> None:
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, f"A {entity.replace('_', ' ')} with the same unique value (reference, registration or license) already exists")

    def flush_or_409(db: Session) -> None:
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, f"A {entity.replace('_', ' ')} with the same unique value (reference, registration or license) already exists")

    @router.get("", response_model=Page[out_schema])
    def list_items(
        request: Request,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        q: str | None = Query(None, max_length=100),
        sort: str | None = None,
        order: str = Query("desc", pattern="^(asc|desc)$"),
        user: User = Depends(read),
        db: Session = Depends(get_db),
    ):
        stmt = select(model).where(model.organization_id == user.organization_id)
        for f in filters:
            raw = request.query_params.get(f)
            if not raw:
                continue
            col = getattr(model, f)
            if isinstance(col.type, Uuid):
                try:
                    raw = uuid.UUID(raw)
                except ValueError:
                    raise HTTPException(422, f"Invalid {f}")
            stmt = stmt.where(col == raw)
        if q and q.strip():
            like = f"%{_escape_like(q.strip().lower())}%"
            stmt = stmt.where(or_(*[func.lower(getattr(model, c)).like(like, escape="\\") for c in search]))
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        sort_key = sort if sort in sort_fields else default_sort
        col = getattr(model, sort_key)
        stmt = stmt.order_by(col.asc() if order == "asc" else col.desc(), model.id)
        rows = list(db.scalars(stmt.limit(page_size).offset((page - 1) * page_size)))
        enrich(db, user.organization_id, model, rows)
        return {"items": rows, "total": total, "page": page, "page_size": page_size}

    if option_label:
        @router.get("/options", response_model=list[Option])
        def options(user: User = Depends(read), db: Session = Depends(get_db)):
            rows = db.scalars(select(model).where(model.organization_id == user.organization_id).order_by(getattr(model, search[0])).limit(500))
            return [Option(id=r.id, label=option_label(r)) for r in rows]

    @router.get("/{item_id}", response_model=out_schema)
    def get_item(item_id: uuid.UUID, user: User = Depends(read), db: Session = Depends(get_db)):
        row = get_row(db, user, item_id)
        enrich(db, user.organization_id, model, [row])
        return row

    @router.post("", response_model=out_schema, status_code=201)
    def create_item(data: create_schema, request: Request, user: User = Depends(write), db: Session = Depends(get_db)):
        values = {k: v for k, v in data.model_dump().items() if v is not None}  # None -> column default / NULL
        check_refs(db, user, values)
        if prepare:
            prepare(values, None)
        row = model(**values, organization_id=user.organization_id)
        db.add(row)
        flush_or_409(db)
        audit.record(db, f"{entity}.created", user=user, ip=client_ip(request), entity_type=entity, entity_id=str(row.id), detail={"label": label(row)})
        save(db)
        enrich(db, user.organization_id, model, [row])
        return row

    @router.patch("/{item_id}", response_model=out_schema)
    def update_item(item_id: uuid.UUID, data: update_schema, request: Request, user: User = Depends(write), db: Session = Depends(get_db)):
        row = get_row(db, user, item_id)
        values = data.model_dump(exclude_unset=True)
        for k, v in values.items():
            if v is None and not model.__table__.c[k].nullable:
                raise HTTPException(422, f"{k} cannot be empty")
        check_refs(db, user, values)
        if prepare:
            prepare(values, row)
        for k, v in values.items():
            setattr(row, k, v)
        audit.record(db, f"{entity}.updated", user=user, ip=client_ip(request), entity_type=entity, entity_id=str(row.id), detail={"label": label(row), "fields": sorted(values)})
        save(db)
        enrich(db, user.organization_id, model, [row])
        return row

    @router.delete("/{item_id}", status_code=204)
    def delete_item(item_id: uuid.UUID, request: Request, user: User = Depends(write), db: Session = Depends(get_db)):
        row = get_row(db, user, item_id)
        audit.record(db, f"{entity}.deleted", user=user, ip=client_ip(request), entity_type=entity, entity_id=str(row.id), detail={"label": label(row)})
        db.delete(row)
        save(db)

    return router
