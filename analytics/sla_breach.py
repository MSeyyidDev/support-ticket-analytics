"""SLA-breach metric (rate by priority + breach trend over time)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px

from analytics.base import Metric


class SLABreachMetric(Metric):
    title = "SLA breaches"
    description = (
        "Share of tickets that exceeded their priority-specific SLA target."
    )

    def compute(self, tickets: pd.DataFrame) -> pd.DataFrame:
        resolved = tickets.dropna(subset=["resolution_hours"]).copy()
        if resolved.empty:
            return pd.DataFrame(
                columns=["priority", "tickets", "breaches", "breach_rate"]
            )
        agg = (
            resolved.groupby("priority")
            .agg(tickets=("id", "count"), breaches=("sla_breached", "sum"))
            .reset_index()
        )
        agg["breach_rate"] = (agg["breaches"] / agg["tickets"]).round(4)
        return agg.sort_values("breach_rate", ascending=False)

    def trend(self, tickets: pd.DataFrame) -> pd.DataFrame:
        resolved = tickets.dropna(subset=["resolution_hours"]).copy()
        if resolved.empty:
            return pd.DataFrame(columns=["month", "breach_rate"])
        resolved["month"] = resolved["created_at"].dt.to_period("M").dt.to_timestamp()
        monthly = (
            resolved.groupby("month")["sla_breached"]
            .mean()
            .round(4)
            .rename("breach_rate")
            .reset_index()
        )
        return monthly

    def top_breach_categories(
        self, tickets: pd.DataFrame, top_n: int = 5
    ) -> pd.DataFrame:
        resolved = tickets.dropna(subset=["resolution_hours"]).copy()
        if resolved.empty:
            return pd.DataFrame(columns=["category", "breach_rate", "tickets"])
        agg = (
            resolved.groupby("category")
            .agg(tickets=("id", "count"), breaches=("sla_breached", "sum"))
            .reset_index()
        )
        agg = agg[agg["tickets"] >= 30]  # require statistical mass
        agg["breach_rate"] = (agg["breaches"] / agg["tickets"]).round(4)
        return agg.sort_values("breach_rate", ascending=False).head(top_n)

    def render(self, df: pd.DataFrame, st: Any) -> None:
        st.subheader(self.title)
        st.caption(self.description)
        if df.empty:
            st.info("No resolved tickets in the selected window.")
            return
        fig = px.bar(
            df,
            x="priority",
            y="breach_rate",
            text=df["breach_rate"].map(lambda v: f"{v:.1%}"),
            color="priority",
        )
        fig.update_layout(yaxis_tickformat=".0%", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
