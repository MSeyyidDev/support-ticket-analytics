"""Synthetic ticket dataset generator.

The :class:`TicketDataGenerator` produces a realistic IT-support workload that
mirrors the schema of an external ``ticket-system-api`` so the dashboard can
later be wired up to a real backend without code changes.

Realism features
----------------
* Volume seasonality: peaks on Monday mornings, dips on weekends, and a
  noticeable surge on the day after Microsoft's "Patch Tuesday" Windows
  updates (second Wednesday of every month).
* Priority-aware SLA targets so SLA-breach analysis is meaningful.
* Per-priority resolution-time distributions (criticals are usually fast,
  lows can drag on for weeks).
* Comment threads of variable length per ticket.

Run it as a module to (re)create ``data/tickets.sqlite`` and
``data/snapshot.parquet``::

    python -m data.generator
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd
from faker import Faker
from sqlalchemy.orm import Session

from data.schema import Comment, Ticket, User, create_schema

LOGGER = logging.getLogger(__name__)

# Hard SLA targets per priority (hours). These are intentionally "tight enough
# to bite" so that the SLA dashboard shows non-trivial breach rates.
SLA_TARGETS_HOURS: dict[str, int] = {
    "critical": 4,
    "high": 8,
    "medium": 24,
    "low": 72,
}

PRIORITY_WEIGHTS: dict[str, float] = {
    "critical": 0.06,
    "high": 0.18,
    "medium": 0.46,
    "low": 0.30,
}

CATEGORIES: list[str] = [
    "Network",
    "Hardware",
    "Software",
    "Account / Access",
    "Email",
    "VPN",
    "Printer",
    "Database",
    "Security",
    "Mobile Device",
    "Telephony",
    "Onboarding",
]

DEPARTMENTS: list[str] = [
    "IT",
    "Engineering",
    "Sales",
    "Marketing",
    "Finance",
    "HR",
    "Operations",
    "Customer Success",
    "Legal",
]

TAG_POOL: list[str] = [
    "vpn",
    "outage",
    "password",
    "windows-update",
    "mac",
    "office365",
    "slow",
    "blocked",
    "permissions",
    "license",
    "wifi",
    "hardware-failure",
    "phishing",
    "two-factor",
    "remote",
]


@dataclass
class GeneratorConfig:
    """Tunable knobs for the generator."""

    n_users: int = 150
    n_tickets: int = 5_000
    n_comments: int = 25_000
    months_back: int = 18
    agent_ratio: float = 0.18  # ~27 agents out of 150 users
    seed: int = 42
    output_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent)


class TicketDataGenerator:
    """Build a realistic IT-support ticket dataset."""

    def __init__(self, config: GeneratorConfig | None = None) -> None:
        self.config = config or GeneratorConfig()
        self.faker = Faker("en_US")
        Faker.seed(self.config.seed)
        random.seed(self.config.seed)

        self.now = datetime(2026, 5, 1, 9, 0, 0)
        self.start = self.now - timedelta(days=30 * self.config.months_back)

        self.users: list[User] = []
        self.agents: list[User] = []
        self.requesters: list[User] = []

    # ------------------------------------------------------------------ users
    def _build_users(self) -> list[User]:
        users: list[User] = []
        n_agents = max(5, int(self.config.n_users * self.config.agent_ratio))

        for i in range(self.config.n_users):
            role = "agent" if i < n_agents else "requester"
            department = "IT" if role == "agent" else random.choice(DEPARTMENTS)
            full_name = self.faker.unique.name()
            email = (
                full_name.lower().replace(" ", ".").replace("'", "")
                + f".{i}@example.com"
            )
            users.append(
                User(
                    id=i + 1,
                    name=full_name,
                    email=email,
                    role=role,
                    department=department,
                    created_at=self.faker.date_time_between(
                        start_date=self.start - timedelta(days=180),
                        end_date=self.start,
                    ),
                )
            )

        self.users = users
        self.agents = [u for u in users if u.role == "agent"]
        self.requesters = [u for u in users if u.role == "requester"]
        return users

    # ---------------------------------------------------------------- tickets
    def _is_patch_tuesday_aftermath(self, dt: datetime) -> bool:
        """The Wednesday/Thursday after the second Tuesday of the month."""
        if dt.weekday() not in (2, 3):  # Wed or Thu
            return False
        # Find the second Tuesday of dt's month
        first_day = dt.replace(day=1)
        offset = (1 - first_day.weekday()) % 7  # 1 = Tuesday
        first_tuesday = first_day + timedelta(days=offset)
        second_tuesday = first_tuesday + timedelta(days=7)
        return dt.date() in (
            (second_tuesday + timedelta(days=1)).date(),
            (second_tuesday + timedelta(days=2)).date(),
        )

    def _seasonality_weight(self, dt: datetime) -> float:
        """Relative likelihood that a ticket is created at *dt*."""
        weekday = dt.weekday()  # 0=Mon ... 6=Sun
        hour = dt.hour

        # Weekend dip
        if weekday >= 5:
            base = 0.25
        else:
            base = 1.0

        # Monday-morning surge (8 - 11)
        if weekday == 0 and 8 <= hour <= 11:
            base *= 2.2

        # General office-hours bell curve (8 - 18)
        if 8 <= hour <= 18:
            base *= 1.0
        elif 6 <= hour <= 22:
            base *= 0.4
        else:
            base *= 0.08

        # Patch-Tuesday aftermath surge
        if self._is_patch_tuesday_aftermath(dt):
            base *= 1.8

        return base

    def _sample_creation_time(self) -> datetime:
        """Rejection-sample a creation timestamp respecting seasonality."""
        total_seconds = int((self.now - self.start).total_seconds())
        for _ in range(40):
            offset = random.randint(0, total_seconds)
            candidate = self.start + timedelta(seconds=offset)
            weight = self._seasonality_weight(candidate)
            if random.random() < weight / 2.2:
                return candidate
        return candidate

    def _resolution_offset_hours(self, priority: str) -> float:
        """Sample a realistic resolution lag per priority."""
        if priority == "critical":
            return random.gauss(3.0, 1.5)
        if priority == "high":
            return random.gauss(7.0, 4.0)
        if priority == "medium":
            return random.gauss(22.0, 14.0)
        return random.gauss(60.0, 40.0)  # low

    def _first_response_offset_minutes(self, priority: str) -> float:
        if priority == "critical":
            return max(2.0, random.gauss(15.0, 8.0))
        if priority == "high":
            return max(5.0, random.gauss(45.0, 25.0))
        if priority == "medium":
            return max(10.0, random.gauss(180.0, 90.0))
        return max(30.0, random.gauss(600.0, 300.0))

    def _build_tickets(self) -> list[Ticket]:
        tickets: list[Ticket] = []
        for ticket_id in range(1, self.config.n_tickets + 1):
            created_at = self._sample_creation_time()
            priority = random.choices(
                population=list(PRIORITY_WEIGHTS.keys()),
                weights=list(PRIORITY_WEIGHTS.values()),
                k=1,
            )[0]
            category = random.choice(CATEGORIES)
            tags = ",".join(
                sorted(set(random.sample(TAG_POOL, k=random.randint(0, 3))))
            )

            requester = random.choice(self.requesters)
            agent = random.choice(self.agents) if random.random() > 0.05 else None

            # Status & timestamps
            age_hours = (self.now - created_at).total_seconds() / 3600.0
            res_lag = max(0.25, self._resolution_offset_hours(priority))

            if age_hours < res_lag:
                status = "in_progress" if random.random() < 0.6 else "open"
                resolved_at = None
            else:
                status = "resolved" if random.random() < 0.85 else "closed"
                resolved_at = created_at + timedelta(hours=res_lag)

            first_response_at = created_at + timedelta(
                minutes=self._first_response_offset_minutes(priority)
            )
            if first_response_at > self.now:
                first_response_at = None

            subject = self.faker.sentence(nb_words=6).rstrip(".")
            description = self.faker.paragraph(nb_sentences=3)

            tickets.append(
                Ticket(
                    id=ticket_id,
                    subject=subject,
                    description=description,
                    status=status,
                    priority=priority,
                    category=category,
                    tags=tags,
                    requester_id=requester.id,
                    agent_id=agent.id if agent else None,
                    created_at=created_at,
                    first_response_at=first_response_at,
                    resolved_at=resolved_at,
                    sla_target_hours=SLA_TARGETS_HOURS[priority],
                )
            )
        return tickets

    # --------------------------------------------------------------- comments
    def _build_comments(self, tickets: list[Ticket]) -> list[Comment]:
        comments: list[Comment] = []
        comment_id = 1
        target = self.config.n_comments
        # Distribute comments across tickets proportionally to age.
        weights = [
            max(1.0, (self.now - t.created_at).total_seconds() / 3600.0)
            for t in tickets
        ]
        chosen = random.choices(tickets, weights=weights, k=target)
        for ticket in chosen:
            author_pool = self.agents if random.random() < 0.6 else self.users
            author = random.choice(author_pool)
            offset_hours = random.uniform(
                0.05,
                max(
                    0.5,
                    (
                        (ticket.resolved_at or self.now) - ticket.created_at
                    ).total_seconds()
                    / 3600.0,
                ),
            )
            comments.append(
                Comment(
                    id=comment_id,
                    ticket_id=ticket.id,
                    author_id=author.id,
                    body=self.faker.paragraph(nb_sentences=2),
                    created_at=ticket.created_at + timedelta(hours=offset_hours),
                )
            )
            comment_id += 1
        return comments

    # --------------------------------------------------------------- persist
    def _persist(
        self,
        users: Iterable[User],
        tickets: Iterable[Ticket],
        comments: Iterable[Comment],
    ) -> tuple[Path, Path]:
        out_dir = self.config.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        sqlite_path = out_dir / "tickets.sqlite"
        parquet_path = out_dir / "snapshot.parquet"

        if sqlite_path.exists():
            sqlite_path.unlink()

        # Build the parquet snapshot BEFORE handing the ORM objects to the
        # session — once the session commits, accessing instance attributes
        # would raise ``DetachedInstanceError``.
        ticket_records = [
            {
                "id": t.id,
                "subject": t.subject,
                "status": t.status,
                "priority": t.priority,
                "category": t.category,
                "tags": t.tags,
                "requester_id": t.requester_id,
                "agent_id": t.agent_id,
                "created_at": t.created_at,
                "first_response_at": t.first_response_at,
                "resolved_at": t.resolved_at,
                "sla_target_hours": t.sla_target_hours,
            }
            for t in tickets
        ]

        engine = create_schema(f"sqlite:///{sqlite_path}")
        with Session(engine) as session:
            session.add_all(list(users))
            session.flush()
            session.add_all(list(tickets))
            session.flush()
            session.add_all(list(comments))
            session.commit()

        pd.DataFrame(ticket_records).to_parquet(parquet_path, index=False)
        return sqlite_path, parquet_path

    # ------------------------------------------------------------------ main
    def generate(self) -> dict[str, int]:
        """Generate the full dataset and persist it. Returns row counts."""
        LOGGER.info("Building users ...")
        users = self._build_users()
        LOGGER.info("Building tickets ...")
        tickets = self._build_tickets()
        LOGGER.info("Building comments ...")
        comments = self._build_comments(tickets)
        LOGGER.info("Persisting ...")
        sqlite_path, parquet_path = self._persist(users, tickets, comments)

        return {
            "users": len(users),
            "tickets": len(tickets),
            "comments": len(comments),
            "sqlite_path": str(sqlite_path),
            "parquet_path": str(parquet_path),
        }


def main() -> None:  # pragma: no cover - CLI entry
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    stats = TicketDataGenerator().generate()
    LOGGER.info("Done: %s", stats)


if __name__ == "__main__":  # pragma: no cover
    main()
