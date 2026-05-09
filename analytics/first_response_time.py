"""First-response-time metric (time-to-first-touch in minutes)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px

from analytics.base import Metric


class FirstResponseTimeMetric(Metric):
    title = "First response time"
    description = "Minutes between ticket creation and first agent response."

    def compute(self, tickets: pd.DataFrame) -> pd.DataFrame:
        df = tickets.dropna(subset=["first_response_minutes"]).copy()
        if df.empty:
            return pd.DataFrame(columns=["priority", "first_response_minutes"])
        cutoff = df["first_response_minutes"].quantile(0.99)
        df = df[df["first_response_minutes"] <= cutoff]
        return df[["priority", "first_response_minutes"]]

    def summary(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=["priority", "p50_min", "p90_min", "n"])
        agg = (
            df.groupby("priority")["first_response_minutes"]
            .agg(p50_min="median", p90_min=lambda s: s.quantile(0.9), n="count")
            .round(1)
            .reset_index()
        )
        return agg

    def render(self, df: pd.DataFrame, st: Any) -> None:
        st.subheader(self.title)
        st.caption(self.description)
        if df.empty:
            st.info("No first-response data.")
            return
        fig = px.box(
            df,
            x="priority",
            y="first_response_minutes",
            points=False,
            labels={"first_response_minutes": "Minutes to first response"},
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(self.summary(df), use_container_width=True, hide_index=True)
