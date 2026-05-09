"""Smoke tests for the synthetic data generator.

The full generator is too slow for unit tests, so we run it with a tiny
configuration and assert on shape, schema, and basic invariants.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data.generator import (
    SLA_TARGETS_HOURS,
    GeneratorConfig,
    TicketDataGenerator,
)
from data.loader import TicketDataLoader


@pytest.fixture(scope="module")
def small_dataset(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("ds")
    cfg = GeneratorConfig(
        n_users=20,
        n_tickets=120,
        n_comments=300,
        months_back=3,
        agent_ratio=0.25,
        seed=7,
        output_dir=out,
    )
    TicketDataGenerator(cfg).generate()
    return out


def test_generator_creates_artifacts(small_dataset: Path) -> None:
    assert (small_dataset / "tickets.sqlite").exists()
    assert (small_dataset / "snapshot.parquet").exists()


def test_loader_returns_expected_row_counts(small_dataset: Path) -> None:
    ds = TicketDataLoader(data_dir=small_dataset).load()
    assert len(ds.users) == 20
    assert len(ds.tickets) == 120
    assert len(ds.comments) == 300


def test_loader_derives_columns(small_dataset: Path) -> None:
    ds = TicketDataLoader(data_dir=small_dataset).load()
    cols = set(ds.tickets.columns)
    for required in ("resolution_hours", "first_response_minutes", "sla_breached", "is_open"):
        assert required in cols


def test_sla_targets_match_priority(small_dataset: Path) -> None:
    ds = TicketDataLoader(data_dir=small_dataset).load()
    for prio, hrs in SLA_TARGETS_HOURS.items():
        sub = ds.tickets[ds.tickets["priority"] == prio]
        if not sub.empty:
            assert (sub["sla_target_hours"] == hrs).all()


def test_parquet_snapshot_matches_sqlite(small_dataset: Path) -> None:
    ds = TicketDataLoader(data_dir=small_dataset).load()
    parquet = pd.read_parquet(small_dataset / "snapshot.parquet")
    assert len(parquet) == len(ds.tickets)
    assert set(parquet["priority"].unique()).issubset(SLA_TARGETS_HOURS.keys())
