"""Notification center: list, mark read, and refresh smart alerts.

Notifications with user_id NULL are visible to the whole organization; ones with a user_id only to
that user. Read state is stored per user, so reading an alert never hides it from a colleague.
Refreshing runs the smart-alert rules for the caller's organization; each condition is raised once.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.models import Notification, NotificationRead, User
from app.schemas.analytics import NotificationList, NotificationOut, RefreshOut
from app.services import alerts

router = APIRouter(prefix="/notifications", tags=["notifications"])
refresh_limit = rate_limit("notif-refresh", 30, 60)  # per IP, in memory


def _visible(user: User):
    return (Notification.organization_id == user.organization_id, or_(Notification.user_id.is_(None), Notification.user_id == user.id))


def _unread_count(db: Session, user: User) -> int:
    read = select(NotificationRead.notification_id).where(NotificationRead.user_id == user.id)
    return db.scalar(select(func.count()).select_from(Notification).where(*_visible(user), Notification.id.not_in(read))) or 0


@router.get("", response_model=NotificationList)
def list_notifications(
    unread_only: bool = False, limit: int = Query(30, ge=1, le=100),
    user: User = Depends(require("analytics:read")), db: Session = Depends(get_db),
):
    read_ids = set(db.scalars(select(NotificationRead.notification_id).where(NotificationRead.user_id == user.id)))
    stmt = select(Notification).where(*_visible(user))
    if unread_only:
        stmt = stmt.where(Notification.id.not_in(list(read_ids))) if read_ids else stmt
    rows = list(db.scalars(stmt.order_by(Notification.created_at.desc(), Notification.id).limit(limit)))
    items = [NotificationOut.model_validate(n).model_copy(update={"is_read": n.id in read_ids}) for n in rows]
    return NotificationList(items=items, unread_count=_unread_count(db, user))


def _mark(db: Session, user: User, ids: list[uuid.UUID]) -> None:
    if not ids:
        return
    have = set(db.scalars(select(NotificationRead.notification_id).where(NotificationRead.user_id == user.id, NotificationRead.notification_id.in_(ids))))
    now = datetime.now(timezone.utc)
    for i in ids:
        if i not in have:
            db.add(NotificationRead(notification_id=i, user_id=user.id, read_at=now))
    try:
        db.commit()
    except IntegrityError:  # a double click marked it already
        db.rollback()


@router.post("/read-all", response_model=RefreshOut)
def read_all(user: User = Depends(require("analytics:read")), db: Session = Depends(get_db)):
    read = select(NotificationRead.notification_id).where(NotificationRead.user_id == user.id)
    ids = list(db.scalars(select(Notification.id).where(*_visible(user), Notification.id.not_in(read))))
    _mark(db, user, ids)
    return RefreshOut(created=0, unread_count=_unread_count(db, user))


@router.post("/refresh", response_model=RefreshOut, dependencies=[Depends(refresh_limit)])
def refresh(user: User = Depends(require("analytics:read")), db: Session = Depends(get_db)):
    created = alerts.sync(db, user.organization_id, datetime.now(timezone.utc))
    return RefreshOut(created=created, unread_count=_unread_count(db, user))


@router.post("/{notification_id}/read", response_model=RefreshOut)
def mark_read(notification_id: uuid.UUID, user: User = Depends(require("analytics:read")), db: Session = Depends(get_db)):
    found = db.scalar(select(Notification.id).where(Notification.id == notification_id, *_visible(user)))
    if not found:
        raise HTTPException(404, "Notification not found")
    _mark(db, user, [notification_id])
    return RefreshOut(created=0, unread_count=_unread_count(db, user))
