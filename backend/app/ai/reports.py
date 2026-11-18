"""Executive reports: deterministic sections built from real data, plus an optional AI-written summary."""
from __future__ import annotations

import json
from datetime import datetime

from app.ai.prompts import REPORT_SYSTEM_PROMPT
from app.ai.providers.base import AIError, AIProvider
from app.services import insights


def _n(x, digits: int = 0) -> str:
    return "n/a" if x is None else f"{x:,.{digits}f}"


def build_sections(f: dict) -> list[dict]:
    fl, dl, fu, mt, dc, dr, sc = f["fleet"], f["deliveries"], f["fuel"], f["maintenance"], f["documents"], f["drivers"], f["screening"]
    days = f["period"]["days"]
    vs = fl["vehicles_by_status"]

    deliveries = [f"{dl['delivered']} delivered in the last {days} days, {dl['created']} new orders created."]
    if dl["on_time_rate_pct"] is None:
        deliveries.append("On-time rate: not enough data (needs delivered orders that had a deadline).")
    else:
        deliveries.append(f"On-time rate: {dl['on_time_rate_pct']}% ({dl['on_time']} of {dl['delivered_with_deadline']} delivered orders with a deadline).")
    deliveries.append(f"{dl['open_now']} deliveries are open now; {dl['open_past_deadline']} of them are past their deadline.")

    fuel = [f"{_n(fu['liters'], 1)} L bought in {fu['fills']} purchases, total cost {_n(fu['cost'], 2)} (no currency)."]
    if fu["cost_per_liter"] is not None:
        fuel.append(f"Average price per litre: {_n(fu['cost_per_liter'], 2)}.")
    if fu["cost_change_pct"] is not None:
        fuel.append(f"Cost changed {fu['cost_change_pct']:+.1f}% against the previous {days} days ({_n(fu['previous_period']['cost'], 2)}).")
    for v in fu["top_vehicles_by_cost"]:
        fuel.append(f"{v['registration']}: {_n(v['cost'], 2)} for {_n(v['liters'], 1)} L.")

    maint = [f"{mt['completed']} jobs completed (cost {_n(mt['completed_cost'], 2)}, no currency).", f"{mt['overdue_now']} scheduled jobs are overdue; {mt['due_next_14_days']} are due in the next 14 days."]

    drivers = [f"{d['driver']}: {d['on_time_rate_pct']}% on time ({d['on_time']} of {d['delivered']})." for d in dr["best_on_time"]]
    drivers += [f"Needs attention: {d['driver']} at {d['on_time_rate_pct']}% on time ({d['late']} late of {d['delivered']})." for d in dr["lowest_on_time"]]
    if not drivers:
        drivers = ["Not enough data: each driver needs at least 3 delivered orders with deadlines in the period."]

    attention: list[str] = []
    if dc["expired"] or dc["expiring_within_30_days"]:
        attention.append(f"Documents: {dc['expired']} expired and {dc['expiring_within_30_days']} expiring within 30 days.")
    attention += [f"[{i['severity']}] {i['title']}: {i['detail']}" for i in sc["top_fuel_anomalies"]]
    attention += [f"Delivery {i['reference']} ({i['level']}): {'; '.join(i['reasons'])}" for i in sc["top_delivery_risks"]]
    attention += [f"Vehicle {i['vehicle']} (high maintenance risk): {'; '.join(i['reasons'])}" for i in sc["top_maintenance_risks"]]
    if not attention:
        attention = ["Nothing flagged by the automatic checks."]

    return [
        {"heading": "Fleet snapshot", "bullets": [f"{fl['vehicles_total']} vehicles: {vs.get('active', 0)} active, {vs.get('idle', 0)} idle, {vs.get('maintenance', 0)} in maintenance, {vs.get('retired', 0)} retired.", f"{fl['drivers_total']} drivers."]},
        {"heading": "Deliveries", "bullets": deliveries},
        {"heading": "Fuel", "bullets": fuel},
        {"heading": "Maintenance", "bullets": maint},
        {"heading": "Drivers", "bullets": drivers},
        {"heading": "Needs attention", "bullets": attention},
        {"heading": "Data notes", "bullets": f["data_notes"]},
    ]


def narrative(provider: AIProvider, facts: dict) -> str:
    messages = [{"role": "system", "content": REPORT_SYSTEM_PROMPT}, {"role": "user", "content": "Facts (JSON):\n" + json.dumps(facts, default=str)}]
    text = provider.chat(messages, None, temperature=0.3).content.strip()
    if not text:
        raise AIError(502, "The AI provider returned an empty summary.")
    return text


def build_report(data: insights.OrgData, now: datetime, days: int, provider: AIProvider | None) -> dict:
    facts = insights.period_facts(data, now, days)
    text, note, model = None, None, None
    if provider is None:
        note = "The written summary was skipped because AI is not configured (set GROQ_API_KEY in the backend .env). The figures below are complete."
    else:
        try:
            text, model = narrative(provider, facts), provider.model
        except AIError as e:
            note = f"The written summary could not be generated: {e.message} The figures below are complete."
    return {
        "title": f"Fleet report: last {days} days", "days": days, "generated_at": now, "sections": build_sections(facts),
        "facts": facts, "narrative": text, "narrative_note": note, "model": model,
    }
