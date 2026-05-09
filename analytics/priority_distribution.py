"""Priority-distribution metric."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px

from analytics.base import Metric


_ORDER = ["critical", "high", "medium", "low"]


class PriorityDistributionMetric(Metric):
    title = "Priority distribution"
    description = "Share of tickets per priority level."

    def compute(self, tickets: pd.DataFrame) -> pd.DataFrame:
        if tickets.empty:
            return pd.DataFrame(columns=["priority", "tickets", "share"])
        counts = (
            tickets.groupby("priority")
            .size()
            .rename("tickets")
            .reset_index()
        )
        counts["share"] = (counts["tickets"] / counts["tickets"].sum()).round(4)
        counts["priority"] = pd.Categorical(
            counts["priority"], categories=_ORDER, ordered=True
        )
        return counts.sort_values("priority").reset_index(drop=True)

    def render(self, df: pd.DataFrame, st: Any) -> None:
        st.subheader(self.title)
        st.caption(self.description)
        if df.empty:
            st.info("No tickets available.")
            return
        fig = px.bar(
            df,
            x="priority",
            y="tickets",
            text="tickets",
            color="priority",
            category_orders={"priority": _ORDER},
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
