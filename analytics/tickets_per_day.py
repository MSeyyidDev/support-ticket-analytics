"""Tickets-per-day metric with rolling 7-day average."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px

from analytics.base import Metric


class TicketsPerDayMetric(Metric):
    title = "Tickets per day"
    description = "Daily ticket volume with a 7-day rolling average."

    def compute(self, tickets: pd.DataFrame) -> pd.DataFrame:
        if tickets.empty:
            return pd.DataFrame(columns=["date", "tickets", "rolling_7d"])

        daily = (
            tickets.assign(date=tickets["created_at"].dt.floor("D"))
            .groupby("date")
            .size()
            .rename("tickets")
            .reset_index()
            .sort_values("date")
        )
        daily["rolling_7d"] = (
            daily["tickets"].rolling(window=7, min_periods=1).mean().round(2)
        )
        return daily

    def render(self, df: pd.DataFrame, st: Any) -> None:
        st.subheader(self.title)
        st.caption(self.description)
        if df.empty:
            st.info("No tickets in the selected window.")
            return
        long = df.melt(
            id_vars="date",
            value_vars=["tickets", "rolling_7d"],
            var_name="series",
            value_name="value",
        )
        fig = px.line(
            long,
            x="date",
            y="value",
            color="series",
            labels={"value": "Tickets", "date": "Date"},
        )
        fig.update_layout(legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)
