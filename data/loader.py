"""Loader that turns the generated dataset into analysis-ready DataFrames."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine


DEFAULT_DATA_DIR = Path(__file__).resolve().parent


@dataclass
class TicketDataset:
    """Bundle of DataFrames returned by :class:`TicketDataLoader`."""

    tickets: pd.DataFrame
    users: pd.DataFrame
    comments: pd.DataFrame

    def joined(self) -> pd.DataFrame:
        """Tickets enriched with agent + requester names."""
        agents = self.users.rename(
            columns={
                "id": "agent_id",
                "name": "agent_name",
                "department": "agent_department",
            }
        )[["agent_id", "agent_name", "agent_department"]]
        requesters = self.users.rename(
            columns={
                "id": "requester_id",
                "name": "requester_name",
                "department": "requester_department",
            }
        )[["requester_id", "requester_name", "requester_department"]]

        df = self.tickets.merge(agents, on="agent_id", how="left")
        df = df.merge(requesters, on="requester_id", how="left")
        return df


class TicketDataLoader:
    """Load the generated SQLite dataset into pandas DataFrames.

    The class is intentionally narrow: the dashboard talks to *this* loader,
    never directly to SQLAlchemy. Swapping it out for an HTTP client that
    consumes ``ticket-system-api`` is therefore a one-class change.
    """

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self.sqlite_path = self.data_dir / "tickets.sqlite"

    # --------------------------------------------------------------- helpers
    def _engine(self):
        if not self.sqlite_path.exists():
            raise FileNotFoundError(
                f"Dataset not found at {self.sqlite_path}. "
                "Run `python -m data.generator` first."
            )
        return create_engine(f"sqlite:///{self.sqlite_path}", future=True)

    # ----------------------------------------------------------------- load
    def load(self) -> TicketDataset:
        engine = self._engine()
        tickets = pd.read_sql_table("tickets", engine)
        users = pd.read_sql_table("users", engine)
        comments = pd.read_sql_table("comments", engine)

        for col in ("created_at", "first_response_at", "resolved_at"):
            if col in tickets.columns:
                tickets[col] = pd.to_datetime(tickets[col], errors="coerce")

        for col in ("created_at",):
            if col in users.columns:
                users[col] = pd.to_datetime(users[col], errors="coerce")
            if col in comments.columns:
                comments[col] = pd.to_datetime(comments[col], errors="coerce")

        # Derived columns used everywhere in analytics.
        tickets["resolution_hours"] = (
            tickets["resolved_at"] - tickets["created_at"]
        ).dt.total_seconds() / 3600.0
        tickets["first_response_minutes"] = (
            tickets["first_response_at"] - tickets["created_at"]
        ).dt.total_seconds() / 60.0
        tickets["sla_breached"] = (
            tickets["resolution_hours"] > tickets["sla_target_hours"]
        ).fillna(False)
        tickets["is_open"] = tickets["status"].isin(["open", "in_progress"])

        return TicketDataset(tickets=tickets, users=users, comments=comments)
