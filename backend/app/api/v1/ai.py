"""AI center: question answering over real data, screening results and executive reports."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import chat, reports
from app.ai.providers import AIProvider, get_optional_provider, get_provider
from app.api.deps import client_ip, require
from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.rbac import permissions_for
from app.models import AIInsight, User
from app.schemas.ai import (
    AnomaliesOut, AskIn, AskOut, DelayRisksOut, MaintenanceForecastOut, ReportIn, ReportListItem, ReportOut, SummaryOut,
)
from app.services import audit, insights

router = APIRouter(tags=["ai"])
REPORT_KIND = "executive_report"
ai_limit = rate_limit("ai", 20, 60)  # per IP, in memory: model calls cost money and time


def _need(user: User, *perms: str) -> None:
    have = permissions_for(user.role_name)
    if not all(p in have for p in perms):
        raise HTTPException(403, "You don't have permission to do that")


def _now() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/ai/summary", response_model=SummaryOut)
def summary(user: User = Depends(require("ai:use")), db: Session = Depends(get_db)):
    """Counts for the dashboard card. Computed from your data with no language model call."""
    have, now = permissions_for(user.role_name), _now()
    data = insights.load(db, user.organization_id)
    return SummaryOut(
        ai_configured=bool(get_settings().groq_api_key),
        fuel_anomalies=insights.fuel_anomalies(data, now)["counts"] if "fuel:read" in have else None,
        delay_risk=insights.delay_risks(data, now)["counts"] if "deliveries:read" in have else None,
        maintenance_risk=insights.maintenance_forecast(data, now)["counts"] if {"maintenance:read", "vehicles:read"} <= have else None,
    )


@router.get("/ai/fuel-anomalies", response_model=AnomaliesOut)
def fuel_anomalies(days: int = Query(90, ge=7, le=365), user: User = Depends(require("ai:use")), db: Session = Depends(get_db)):
    _need(user, "fuel:read")
    return insights.fuel_anomalies(insights.load(db, user.organization_id), _now(), days)


@router.get("/ai/delay-risks", response_model=DelayRisksOut)
def delay_risks(user: User = Depends(require("ai:use")), db: Session = Depends(get_db)):
    _need(user, "deliveries:read")
    return insights.delay_risks(insights.load(db, user.organization_id), _now())


@router.get("/ai/maintenance-forecast", response_model=MaintenanceForecastOut)
def maintenance_forecast(interval_km: int = Query(10_000, ge=1000, le=100_000), user: User = Depends(require("ai:use")), db: Session = Depends(get_db)):
    _need(user, "maintenance:read", "vehicles:read")
    return insights.maintenance_forecast(insights.load(db, user.organization_id), _now(), interval_km)


@router.post("/ai/ask", response_model=AskOut, dependencies=[Depends(ai_limit)])
def ask(
    body: AskIn, request: Request,
    user: User = Depends(require("ai:use")), db: Session = Depends(get_db),
    provider: AIProvider = Depends(get_provider),  # declared after `user`, so sign-in is checked first
):
    result = chat.ask(db, user, body.question.strip(), [m.model_dump() for m in body.history], provider)
    # The audit log keeps which data was read, not the question or the answer text.
    audit.record(db, "ai.ask", user=user, entity_type="ai", ip=client_ip(request),
                 detail={"tools": [t["name"] for t in result["tools_used"]], "question_chars": len(body.question)}, commit=True)
    return AskOut(answer=result["answer"], tools_used=result["tools_used"], model=provider.model, generated_at=_now())


@router.post("/ai/reports", response_model=ReportOut, status_code=201, dependencies=[Depends(ai_limit)])
def create_report(
    body: ReportIn, request: Request,
    user: User = Depends(require("ai:use")), db: Session = Depends(get_db),
    provider: AIProvider | None = Depends(get_optional_provider),
):
    _need(user, "vehicles:read", "drivers:read", "deliveries:read", "fuel:read", "maintenance:read")
    report = reports.build_report(insights.load(db, user.organization_id), _now(), body.days, provider)
    row = AIInsight(organization_id=user.organization_id, kind=REPORT_KIND, title=report["title"], body=report["narrative"] or "", data=jsonable_encoder(report))
    db.add(row)
    audit.record(db, "ai.report.create", user=user, entity_type="ai_report", ip=client_ip(request), detail={"days": body.days, "ai_summary": report["narrative"] is not None})
    db.commit()
    return ReportOut(id=row.id, **report)


def _find_report(db: Session, user: User, report_id: uuid.UUID) -> AIInsight:
    row = db.scalar(select(AIInsight).where(AIInsight.id == report_id, AIInsight.organization_id == user.organization_id, AIInsight.kind == REPORT_KIND))
    if row is None:
        raise HTTPException(404, "Report not found")
    return row


@router.get("/ai/reports", response_model=list[ReportListItem])
def list_reports(user: User = Depends(require("ai:use")), db: Session = Depends(get_db)):
    rows = db.scalars(select(AIInsight).where(AIInsight.organization_id == user.organization_id, AIInsight.kind == REPORT_KIND).order_by(AIInsight.created_at.desc()).limit(20))
    return [ReportListItem(id=r.id, title=r.title, days=r.data["days"], generated_at=r.data["generated_at"], has_narrative=bool(r.body)) for r in rows]


@router.get("/ai/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: uuid.UUID, user: User = Depends(require("ai:use")), db: Session = Depends(get_db)):
    row = _find_report(db, user, report_id)
    return ReportOut(id=row.id, **row.data)


@router.delete("/ai/reports/{report_id}", status_code=204)
def delete_report(report_id: uuid.UUID, request: Request, user: User = Depends(require("ai:use")), db: Session = Depends(get_db)):
    row = _find_report(db, user, report_id)
    db.delete(row)
    audit.record(db, "ai.report.delete", user=user, entity_type="ai_report", entity_id=str(report_id), ip=client_ip(request))
    db.commit()
