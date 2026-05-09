"""Shared pytest fixtures: deterministic mini-dataset for metric tests."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.generator import SLA_TARGETS_HOURS  # noqa: E402


def _make_ticket(
    ticket_id: int,
    created_at: datetime,
    priority: str,
    category: str,
    agent_name: str | None,
    resolution_hours: float | None,
    first_response_minutes: float | None,
    tags: str = "",
) -> dict:
    resolved_at = (
        created_at + timedelta(hours=resolution_hours)
        if resolution_hours is not None
        else None
    )
    first_response_at = (
        created_at + timedelta(minutes=first_response_minutes)
        if first_response_minutes is not None
        else None
    )
    sla = SLA_TARGETS_HOURS[priority]
    return {
        "id": ticket_id,
        "subject": f"Subject {ticket_id}",
        "status": "resolved" if resolution_hours is not None else "open",
        "priority": priority,
        "category": category,
        "tags": tags,
        "requester_id": 100 + ticket_id,
        "agent_id": 1 if agent_name else None,
        "agent_name": agent_name,
        "agent_department": "IT" if agent_name else None,
        "requester_name": f"Requester {ticket_id}",
        "requester_department": "Sales",
        "created_at": created_at,
        "first_response_at": first_response_at,
        "resolved_at": resolved_at,
        "sla_target_hours": sla,
        "resolution_hours": resolution_hours,
        "first_response_minutes": first_response_minutes,
        "sla_breached": (
            (resolution_hours or 0) > sla if resolution_hours is not None else False
        ),
        "is_open": resolution_hours is None,
    }


@pytest.fixture()
def mini_tickets() -> pd.DataFrame:
    """A deterministic 8-row ticket frame covering all metrics."""
    base = datetime(2026, 1, 5, 9, 0)  # Monday morning
    rows = [
        _make_ticket(1, base, "critical", "Network", "Alice", 2.0, 10, "vpn"),
        _make_ticket(2, base + timedelta(hours=1), "critical", "Network", "Alice", 6.0, 30, "vpn,outage"),
        _make_ticket(3, base + timedelta(days=1), "high", "Email", "Bob", 5.0, 20, "office365"),
        _make_ticket(4, base + timedelta(days=1, hours=2), "high", "Email", "Bob", 15.0, 90, "office365,phishing"),
        _make_ticket(5, base + timedelta(days=2), "medium", "Software", "Cara", 12.0, 90, "license"),
        _make_ticket(6, base + timedelta(days=2, hours=4), "medium", "Software", "Cara", 40.0, 200, "license,slow"),
        _make_ticket(7, base + timedelta(days=3), "low", "Printer", None, 100.0, 600, ""),
        _make_ticket(8, base + timedelta(days=4), "low", "Printer", "Bob", None, None, ""),
    ]
    return pd.DataFrame(rows)
