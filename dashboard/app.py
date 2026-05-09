"""Multipage Streamlit entry point.

Run with::

    streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Allow `streamlit run dashboard/app.py` from any cwd.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.state import (  # noqa: E402  (path tweak above)
    apply_filters,
    load_dataset,
    render_sidebar_filters,
)

PAGES = {
    "Overview": "_render_overview",
    "Volume": "_render_volume",
    "Performance": "_render_performance",
    "SLA": "_render_sla",
    "Agents": "_render_agents",
    "Categories & Tags": "_render_categories",
}


def main() -> None:
    st.set_page_config(
        page_title="Support Ticket Analytics",
        page_icon=":bar_chart:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("Support Ticket Analytics")
    st.caption(
        "Operational insights from synthetic IT-support tickets — "
        "schema-compatible with `ticket-system-api`."
    )

    try:
        dataset = load_dataset()
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.stop()
        return

    tickets = dataset.tickets
    filters = render_sidebar_filters(tickets)
    filtered = apply_filters(tickets, filters)

    page = st.sidebar.radio("Page", list(PAGES.keys()))
    st.sidebar.metric("Tickets in selection", f"{len(filtered):,}")

    handler = globals()[PAGES[page]]
    handler(filtered)


# --------------------------------------------------------------------- pages
def _render_overview(df) -> None:
    from analytics import TicketsPerDayMetric

    st.header("Overview")
    total = len(df)
    open_count = int(df["is_open"].sum()) if not df.empty else 0
    resolved = df.dropna(subset=["resolution_hours"]) if not df.empty else df
    avg_res = float(resolved["resolution_hours"].mean()) if not resolved.empty else 0.0
    breach_rate = (
        float(resolved["sla_breached"].mean()) if not resolved.empty else 0.0
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total tickets", f"{total:,}")
    c2.metric("Currently open", f"{open_count:,}")
    c3.metric("Avg resolution (h)", f"{avg_res:.1f}")
    c4.metric("SLA breach rate", f"{breach_rate:.1%}")

    metric = TicketsPerDayMetric()
    metric.render(metric.compute(df), st)


def _render_volume(df) -> None:
    from analytics import TicketsPerDayMetric

    st.header("Volume")
    TicketsPerDayMetric().render(TicketsPerDayMetric().compute(df), st)

    st.subheader("Hour-of-day x day-of-week heatmap")
    if df.empty:
        st.info("No tickets in the selected window.")
    else:
        tmp = df.copy()
        tmp["hour"] = tmp["created_at"].dt.hour
        tmp["weekday"] = tmp["created_at"].dt.day_name()
        pivot = (
            tmp.groupby(["weekday", "hour"]).size().rename("tickets").reset_index()
        )
        order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        import plotly.express as px

        fig = px.density_heatmap(
            pivot,
            x="hour",
            y="weekday",
            z="tickets",
            category_orders={"weekday": order},
            color_continuous_scale="Blues",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Monthly comparison")
    if not df.empty:
        monthly = (
            df.assign(month=df["created_at"].dt.to_period("M").dt.to_timestamp())
            .groupby("month")
            .size()
            .rename("tickets")
            .reset_index()
        )
        import plotly.express as px

        fig = px.bar(monthly, x="month", y="tickets")
        st.plotly_chart(fig, use_container_width=True)


def _render_performance(df) -> None:
    from analytics import FirstResponseTimeMetric, ResolutionTimeMetric

    st.header("Performance")
    for dim in ("priority", "category", "agent_name"):
        m = ResolutionTimeMetric(by=dim)
        m.render(m.compute(df), st)
    frt = FirstResponseTimeMetric()
    frt.render(frt.compute(df), st)


def _render_sla(df) -> None:
    from analytics import SLABreachMetric

    st.header("SLA")
    metric = SLABreachMetric()
    metric.render(metric.compute(df), st)

    st.subheader("Breach trend over time")
    trend = metric.trend(df)
    if not trend.empty:
        import plotly.express as px

        fig = px.line(trend, x="month", y="breach_rate", markers=True)
        fig.update_layout(yaxis_tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No breach data.")

    st.subheader("Top breach categories")
    top = metric.top_breach_categories(df)
    if not top.empty:
        st.dataframe(top, use_container_width=True, hide_index=True)
    else:
        st.info("Not enough resolved tickets per category.")


def _render_agents(df) -> None:
    from analytics import OpenByAgentMetric, ResolutionTimeMetric

    st.header("Agents")
    by_agent = OpenByAgentMetric()
    by_agent.render(by_agent.compute(df), st)

    st.subheader("Throughput (resolved tickets per agent)")
    th = by_agent.throughput(df)
    if not th.empty:
        st.dataframe(th.head(20), use_container_width=True, hide_index=True)
    else:
        st.info("No throughput data.")

    res_by_agent = ResolutionTimeMetric(by="agent_name")
    res_by_agent.render(res_by_agent.compute(df), st)


def _render_categories(df) -> None:
    from analytics import CategoryFrequencyMetric

    st.header("Categories & Tags")
    metric = CategoryFrequencyMetric()
    metric.render(metric.compute(df), st)

    st.subheader("Tag co-occurrence (top pairs)")
    co = metric.cooccurrence(df)
    if not co.empty:
        st.dataframe(co, use_container_width=True, hide_index=True)
    else:
        st.info("No co-occurring tags in the selected window.")

    st.subheader("Treemap: category x priority")
    if not df.empty:
        import plotly.express as px

        tm = (
            df.groupby(["category", "priority"])
            .size()
            .rename("tickets")
            .reset_index()
        )
        fig = px.treemap(tm, path=["category", "priority"], values="tickets")
        st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
