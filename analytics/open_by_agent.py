"""Open-tickets-per-agent metric."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px

from analytics.base import Metric


class OpenByAgentMetric(Metric):
    title = "Open tickets per agent"
    description = "Current workload distribution across agents."

    def compute(self, tickets: pd.DataFrame) -> pd.DataFrame:
        if tickets.empty:
            return pd.DataFrame(columns=["agent_name", "open_tickets"])
        open_tickets = tickets[tickets["is_open"]].copy()
        if "agent_name" not in open_tickets.columns:
            return pd.DataFrame(columns=["agent_name", "open_tickets"])
        agg = (
            open_tickets.groupby("agent_name", dropna=False)
            .size()
            .rename("open_tickets")
            .reset_index()
            .sort_values("open_tickets", ascending=False)
        )
        agg["agent_name"] = agg["agent_name"].fillna("Unassigned")
        return agg

    def throughput(self, tickets: pd.DataFrame) -> pd.DataFrame:
        if tickets.empty or "agent_name" not in tickets.columns:
            return pd.DataFrame(columns=["agent_name", "resolved_tickets"])
        resolved = tickets.dropna(subset=["resolved_at"]).copy()
        agg = (
            resolved.groupby("agent_name", dropna=False)
            .size()
            .rename("resolved_tickets")
            .reset_index()
            .sort_values("resolved_tickets", ascending=False)
        )
        return agg

    def render(self, df: pd.DataFrame, st: Any) -> None:
        st.subheader(self.title)
        st.caption(self.description)
        if df.empty:
            st.info("No open tickets.")
            return
        top = df.head(20)
        fig = px.bar(
            top,
            x="open_tickets",
            y="agent_name",
            orientation="h",
            text="open_tickets",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
