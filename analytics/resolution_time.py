"""Resolution-time metric."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px

from analytics.base import Metric


class ResolutionTimeMetric(Metric):
    title = "Resolution time"
    description = (
        "Distribution of resolution time (hours) grouped by a chosen dimension."
    )

    def __init__(self, by: str = "priority") -> None:
        if by not in {"priority", "category", "agent_name"}:
            raise ValueError(f"Unsupported grouping dimension: {by}")
        self.by = by

    def compute(self, tickets: pd.DataFrame) -> pd.DataFrame:
        resolved = tickets.dropna(subset=["resolution_hours"]).copy()
        if resolved.empty or self.by not in resolved.columns:
            return pd.DataFrame(columns=[self.by, "resolution_hours"])
        # Trim insane outliers above the 99th percentile so plots stay readable.
        cutoff = resolved["resolution_hours"].quantile(0.99)
        resolved = resolved[resolved["resolution_hours"] <= cutoff]
        return resolved[[self.by, "resolution_hours"]]

    def summary(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=[self.by, "median_h", "mean_h", "n"])
        agg = (
            df.groupby(self.by)["resolution_hours"]
            .agg(median_h="median", mean_h="mean", n="count")
            .round(2)
            .reset_index()
            .sort_values("median_h")
        )
        return agg

    def render(self, df: pd.DataFrame, st: Any) -> None:
        st.subheader(f"{self.title} by {self.by}")
        st.caption(self.description)
        if df.empty:
            st.info("No resolved tickets to display.")
            return
        fig = px.box(
            df,
            x=self.by,
            y="resolution_hours",
            points=False,
            labels={"resolution_hours": "Resolution time (h)"},
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(self.summary(df), use_container_width=True, hide_index=True)
