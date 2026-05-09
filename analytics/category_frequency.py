"""Category-frequency metric (top categories + tag co-occurrence)."""

from __future__ import annotations

from itertools import combinations
from typing import Any

import pandas as pd
import plotly.express as px

from analytics.base import Metric


class CategoryFrequencyMetric(Metric):
    title = "Category frequency"
    description = "Most common ticket categories and tag co-occurrence."

    def compute(self, tickets: pd.DataFrame) -> pd.DataFrame:
        if tickets.empty:
            return pd.DataFrame(columns=["category", "tickets"])
        counts = (
            tickets.groupby("category")
            .size()
            .rename("tickets")
            .reset_index()
            .sort_values("tickets", ascending=False)
        )
        return counts

    def cooccurrence(self, tickets: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        if tickets.empty or "tags" not in tickets.columns:
            return pd.DataFrame(columns=["tag_a", "tag_b", "count"])
        pairs: dict[tuple[str, str], int] = {}
        for raw in tickets["tags"].dropna():
            tags = sorted({t for t in str(raw).split(",") if t})
            for a, b in combinations(tags, 2):
                pairs[(a, b)] = pairs.get((a, b), 0) + 1
        df = pd.DataFrame(
            [
                {"tag_a": a, "tag_b": b, "count": c}
                for (a, b), c in pairs.items()
            ]
        )
        return df.sort_values("count", ascending=False).head(top_n)

    def render(self, df: pd.DataFrame, st: Any) -> None:
        st.subheader(self.title)
        st.caption(self.description)
        if df.empty:
            st.info("No tickets available.")
            return
        fig = px.bar(
            df,
            x="tickets",
            y="category",
            orientation="h",
            text="tickets",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
