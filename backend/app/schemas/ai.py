import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]  # the client can never inject system or tool messages
    content: str = Field(min_length=1, max_length=4000)


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=12)


class ToolUsed(BaseModel):
    name: str
    arguments: dict


class AskOut(BaseModel):
    answer: str
    tools_used: list[ToolUsed]
    model: str
    generated_at: datetime


class AnomalyOut(BaseModel):
    id: str
    kind: str
    severity: Literal["critical", "warning", "info"]
    title: str
    detail: str
    vehicle_id: str
    registration: str
    transaction_id: str
    occurred_at: datetime
    evidence: dict


class AnomaliesOut(BaseModel):
    days: int
    items: list[AnomalyOut]
    counts: dict[str, int]
    stats: dict[str, int]
    methods: list[str]
    limitations: list[str]


class DelayRiskOut(BaseModel):
    delivery_id: str
    reference: str
    status: str
    deadline: datetime
    minutes_left: int
    estimated_trip_minutes: int | None
    score: int
    level: Literal["late", "high", "medium", "low"]
    reasons: list[str]
    vehicle: str | None
    driver: str | None
    dest_address: str


class DelayRisksOut(BaseModel):
    items: list[DelayRiskOut]
    counts: dict[str, int]
    open_deliveries: int
    without_deadline: int
    methods: list[str]
    assumptions: dict[str, float]


class MaintenanceRiskOut(BaseModel):
    vehicle_id: str
    registration: str
    label: str
    risk: Literal["high", "medium", "low"]
    current_km: int
    km_since_service: int | None
    km_per_day: float | None
    predicted_due_date: date | None
    reasons: list[str]


class MaintenanceForecastOut(BaseModel):
    items: list[MaintenanceRiskOut]
    counts: dict[str, int]
    interval_km: int
    methods: list[str]


class SummaryOut(BaseModel):
    ai_configured: bool
    fuel_anomalies: dict[str, int] | None
    delay_risk: dict[str, int] | None
    maintenance_risk: dict[str, int] | None


class ReportIn(BaseModel):
    days: Literal[7, 30, 90] = 30


class ReportSection(BaseModel):
    heading: str
    bullets: list[str]


class ReportOut(BaseModel):
    id: uuid.UUID | None = None
    title: str
    days: int
    generated_at: datetime
    sections: list[ReportSection]
    facts: dict
    narrative: str | None
    narrative_note: str | None
    model: str | None


class ReportListItem(BaseModel):
    id: uuid.UUID
    title: str
    days: int
    generated_at: datetime
    has_narrative: bool
