"""Backlog-trend metric: opened vs. resolved per day, with running backlog."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go

from analytics.base import Metric


class BacklogTrendMetric(Metric):
    title = "Backlog trend"
    description = "Opened vs. resolved tickets per day and resulting backlog."

    def compute(self, tickets: pd.DataFrame) -> pd.DataFrame:
        if tickets.empty:
            return pd.DataFrame(columns=["date", "opened", "resolved", "backlog"])
        opened = (
            tickets.assign(date=tickets["created_at"].dt.floor("D"))
            .groupby("date")
            .size()
            .rename("opened")
        )
        resolved = (
            tickets.dropna(subset=["resolved_at"])
            .assign(date=lambda d: d["resolved_at"].dt.floor("D"))
            .groupby("date")
            .size()
            .rename("resolved")
        )
        df = (
            pd.concat([opened, resolved], axis=1)
            .fillna(0)
            .sort_index()
            .reset_index()
        )
        df["backlog"] = (df["opened"] - df["resolved"]).cumsum().astype(int)
        df["opened"] = df["opened"].astype(int)
        df["resolved"] = df["resolved"].astype(int)
        return df

    def render(self, df: pd.DataFrame, st: Any) -> None:
        st.subheader(self.title)
        st.caption(self.description)
        if df.empty:
            st.info("No tickets to show.")
            return
        fig = go.Figure()
        fig.add_trace(
            go.Bar(x=df["date"], y=df["opened"], name="Opened", opacity=0.6)
        )
        fig.add_trace(
            go.Bar(
                x=df["date"],
                y=df["resolved"],
                name="Resolved",
                opacity=0.6,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["backlog"],
                name="Backlog",
                yaxis="y2",
                mode="lines",
            )
        )
        fig.update_layout(
            barmode="overlay",
            yaxis=dict(title="Tickets / day"),
            yaxis2=dict(title="Backlog", overlaying="y", side="right"),
            legend=dict(orientation="h"),
        )
        st.plotly_chart(fig, use_container_width=True)
