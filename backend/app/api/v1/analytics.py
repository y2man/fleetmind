"""Analytics page data plus CSV and PDF exports.

Security: every query is limited to the caller's organization (insights.load), reads need
analytics:read, and each CSV dataset also needs the matching resource permission (a viewer
may export what they can read, nothing else). Every export is written to the audit log.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import client_ip, require
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.rbac import permissions_for
from app.models import User
from app.schemas.analytics import AnalyticsOut
from app.services import analytics, audit, exports, insights

router = APIRouter(prefix="/analytics", tags=["analytics"])
export_limit = rate_limit("export", 20, 60)  # per IP, in memory: exports read the whole data set


def resolve_range(start: date | None, end: date | None, days: int | None) -> tuple[date, date]:
    today = datetime.now(timezone.utc).date()
    if start is None and end is None:
        n = days if days is not None else 30
        if not 1 <= n <= analytics.MAX_RANGE_DAYS:
            raise HTTPException(422, f"days must be between 1 and {analytics.MAX_RANGE_DAYS}")
        return today - timedelta(days=n - 1), today
    if start is None or end is None:
        raise HTTPException(422, "Give both start and end dates, or neither")
    if start > end:
        raise HTTPException(422, "The start date must not be after the end date")
    if end > today:
        raise HTTPException(422, "The end date cannot be in the future")
    if (end - start).days + 1 > analytics.MAX_RANGE_DAYS:
        raise HTTPException(422, f"The range can be at most {analytics.MAX_RANGE_DAYS} days")
    return start, end


@router.get("", response_model=AnalyticsOut)
def get_analytics(
    start: date | None = None, end: date | None = None, days: int | None = Query(None),
    user: User = Depends(require("analytics:read")), db: Session = Depends(get_db),
):
    s, e = resolve_range(start, end, days)
    return analytics.compute(insights.load(db, user.organization_id), s, e, datetime.now(timezone.utc))


@router.get("/export/{dataset}", dependencies=[Depends(export_limit)])
def export_csv(
    dataset: str, request: Request, start: date | None = None, end: date | None = None, days: int | None = Query(None),
    user: User = Depends(require("analytics:read")), db: Session = Depends(get_db),
):
    if dataset not in exports.DATASETS:
        raise HTTPException(404, "Unknown dataset")
    if f"{dataset}:read" not in permissions_for(user.role_name):
        raise HTTPException(403, "You don't have permission to do that")

    if start is None and end is None and days is None:
        headers, rows, filtered = exports.dataset_rows(dataset, insights.load(db, user.organization_id), date(2000, 1, 1), date(2999, 12, 31))
        s, e = None, None
    else:
        s, e = resolve_range(start, end, days)
        headers, rows, filtered = exports.dataset_rows(dataset, insights.load(db, user.organization_id), s, e)

    if len(rows) > exports.MAX_ROWS:
        raise HTTPException(422, f"Too many rows ({len(rows):,}). Choose a shorter date range.")
    audit.record(db, "export.csv", user=user, ip=client_ip(request), entity_type="export", detail={"dataset": dataset, "rows": len(rows), "start": s.isoformat() if filtered and s else None, "end": e.isoformat() if filtered and e else None}, commit=True)
    name = f"fleetmind-{dataset}-{s}-{e}.csv" if filtered and s and e else f"fleetmind-{dataset}.csv"
    return Response(exports.to_csv(headers, rows), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"})


@router.get("/report", dependencies=[Depends(export_limit)])
def export_pdf(
    request: Request, start: date | None = None, end: date | None = None, days: int | None = Query(None),
    user: User = Depends(require("analytics:read")), db: Session = Depends(get_db),
):
    s, e = resolve_range(start, end, days)
    report = analytics.compute(insights.load(db, user.organization_id), s, e, datetime.now(timezone.utc))
    pdf = exports.analytics_pdf(report, user.organization.name)
    audit.record(db, "export.pdf", user=user, ip=client_ip(request), entity_type="export", detail={"report": "analytics", "start": s.isoformat(), "end": e.isoformat()}, commit=True)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="fleetmind-report-{s}-{e}.pdf"', "Cache-Control": "no-store"})
