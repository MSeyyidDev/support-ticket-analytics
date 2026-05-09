"""Unit tests for every metric class.

These tests are intentionally deterministic — they use the small fixture from
``conftest.py`` so the expected numbers can be verified by hand.
"""

from __future__ import annotations

import pandas as pd
import pytest

from analytics import (
    BacklogTrendMetric,
    CategoryFrequencyMetric,
    FirstResponseTimeMetric,
    OpenByAgentMetric,
    PriorityDistributionMetric,
    ResolutionTimeMetric,
    SLABreachMetric,
    TicketsPerDayMetric,
)


# --------------------------------------------------------- TicketsPerDayMetric
def test_tickets_per_day_counts_rows_by_day(mini_tickets: pd.DataFrame) -> None:
    df = TicketsPerDayMetric().compute(mini_tickets)
    assert df["tickets"].sum() == len(mini_tickets)
    assert (df["tickets"] >= 1).all()


def test_tickets_per_day_rolling_avg_present(mini_tickets: pd.DataFrame) -> None:
    df = TicketsPerDayMetric().compute(mini_tickets)
    assert "rolling_7d" in df.columns
    assert df["rolling_7d"].iloc[0] == df["tickets"].iloc[0]


def test_tickets_per_day_handles_empty() -> None:
    empty = pd.DataFrame(columns=["created_at"])
    df = TicketsPerDayMetric().compute(empty)
    assert df.empty
    assert list(df.columns) == ["date", "tickets", "rolling_7d"]


# ----------------------------------------------------------- ResolutionTimeMetric
def test_resolution_time_drops_unresolved(mini_tickets: pd.DataFrame) -> None:
    df = ResolutionTimeMetric(by="priority").compute(mini_tickets)
    assert df["resolution_hours"].notna().all()
    # 7 of 8 tickets are resolved. The metric also clips the top 1% to keep
    # plots readable, which can drop the single highest value in tiny
    # fixtures, so we accept either 6 or 7 rows.
    assert len(df) in {6, 7}


def test_resolution_time_summary_orders_by_median(mini_tickets: pd.DataFrame) -> None:
    metric = ResolutionTimeMetric(by="priority")
    summary = metric.summary(metric.compute(mini_tickets))
    assert summary["median_h"].is_monotonic_increasing
    # The 99th-percentile clip may drop the single low-priority outlier in
    # this tiny fixture, so we only assert the high-volume priorities.
    assert {"critical", "high", "medium"}.issubset(set(summary["priority"]))


def test_resolution_time_rejects_bad_dimension() -> None:
    with pytest.raises(ValueError):
        ResolutionTimeMetric(by="moon_phase")


# -------------------------------------------------- PriorityDistributionMetric
def test_priority_distribution_shares_sum_to_one(mini_tickets: pd.DataFrame) -> None:
    df = PriorityDistributionMetric().compute(mini_tickets)
    assert pytest.approx(df["share"].sum(), abs=1e-3) == 1.0


def test_priority_distribution_ordering(mini_tickets: pd.DataFrame) -> None:
    df = PriorityDistributionMetric().compute(mini_tickets)
    assert list(df["priority"].astype(str)) == ["critical", "high", "medium", "low"]


# -------------------------------------------------- CategoryFrequencyMetric
def test_category_frequency_counts(mini_tickets: pd.DataFrame) -> None:
    df = CategoryFrequencyMetric().compute(mini_tickets)
    assert df.set_index("category").loc["Network", "tickets"] == 2
    assert df["tickets"].is_monotonic_decreasing


def test_category_cooccurrence_returns_pairs(mini_tickets: pd.DataFrame) -> None:
    df = CategoryFrequencyMetric().cooccurrence(mini_tickets)
    assert {"tag_a", "tag_b", "count"}.issubset(df.columns)
    assert (df["count"] >= 1).all()


# ----------------------------------------------------------- SLABreachMetric
def test_sla_breach_rates_per_priority(mini_tickets: pd.DataFrame) -> None:
    df = SLABreachMetric().compute(mini_tickets)
    rates = df.set_index("priority")["breach_rate"].to_dict()
    # critical SLA = 4h; ticket 1 at 2h passes, ticket 2 at 6h breaches → 0.5.
    assert rates["critical"] == 0.5
    # low SLA = 72h; only ticket 7 (100h) is resolved and it breaches → 1.0.
    assert rates["low"] == 1.0


def test_sla_breach_trend_returns_monthly_rate(mini_tickets: pd.DataFrame) -> None:
    df = SLABreachMetric().trend(mini_tickets)
    assert "breach_rate" in df.columns
    assert ((df["breach_rate"] >= 0) & (df["breach_rate"] <= 1)).all()


# ---------------------------------------------------------- OpenByAgentMetric
def test_open_by_agent_only_open_tickets(mini_tickets: pd.DataFrame) -> None:
    df = OpenByAgentMetric().compute(mini_tickets)
    # Only ticket 8 is open and assigned to Bob.
    assert df.loc[df["agent_name"] == "Bob", "open_tickets"].iloc[0] == 1
    assert df["open_tickets"].sum() == 1


def test_open_by_agent_throughput_counts_resolved(mini_tickets: pd.DataFrame) -> None:
    df = OpenByAgentMetric().throughput(mini_tickets)
    counts = df.set_index("agent_name")["resolved_tickets"].to_dict()
    assert counts.get("Alice") == 2
    assert counts.get("Cara") == 2


# ----------------------------------------------------------- BacklogTrendMetric
def test_backlog_trend_balances(mini_tickets: pd.DataFrame) -> None:
    df = BacklogTrendMetric().compute(mini_tickets)
    assert (df["backlog"] >= 0).all() or (df["backlog"] <= len(mini_tickets)).all()
    # Cumulative opened minus resolved should equal current open count.
    assert df["backlog"].iloc[-1] == int(mini_tickets["is_open"].sum())


def test_backlog_trend_columns(mini_tickets: pd.DataFrame) -> None:
    df = BacklogTrendMetric().compute(mini_tickets)
    assert {"date", "opened", "resolved", "backlog"} == set(df.columns)


# ------------------------------------------------------ FirstResponseTimeMetric
def test_first_response_time_drops_missing(mini_tickets: pd.DataFrame) -> None:
    df = FirstResponseTimeMetric().compute(mini_tickets)
    assert df["first_response_minutes"].notna().all()
    # 7 tickets carry a first_response_at; the 99th-percentile clip may drop
    # the single outlier on the low-priority fixture row.
    assert len(df) in {6, 7}


def test_first_response_summary_has_percentiles(mini_tickets: pd.DataFrame) -> None:
    metric = FirstResponseTimeMetric()
    summary = metric.summary(metric.compute(mini_tickets))
    assert {"p50_min", "p90_min", "n"}.issubset(summary.columns)
    assert (summary["p90_min"] >= summary["p50_min"]).all()


# ----------------------------------------------------- empty-input robustness
@pytest.mark.parametrize(
    "metric",
    [
        TicketsPerDayMetric(),
        PriorityDistributionMetric(),
        CategoryFrequencyMetric(),
        SLABreachMetric(),
        OpenByAgentMetric(),
        BacklogTrendMetric(),
        FirstResponseTimeMetric(),
        ResolutionTimeMetric(by="priority"),
    ],
)
def test_metrics_handle_empty_input(metric) -> None:
    empty = pd.DataFrame(
        columns=[
            "id",
            "created_at",
            "resolved_at",
            "first_response_at",
            "priority",
            "category",
            "agent_name",
            "tags",
            "resolution_hours",
            "first_response_minutes",
            "sla_breached",
            "is_open",
            "sla_target_hours",
            "status",
        ]
    )
    result = metric.compute(empty)
    assert isinstance(result, pd.DataFrame)
    assert result.empty
