"""Shared dashboard helpers: cached data loading + global sidebar filters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from data.generator import TicketDataGenerator
from data.loader import TicketDataLoader, TicketDataset

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@st.cache_data(show_spinner="Loading ticket dataset ...")
def _load_dataset() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    data_dir = PROJECT_ROOT / "data"
    if not (data_dir / "tickets.sqlite").exists():
        TicketDataGenerator().generate()
    loader = TicketDataLoader(data_dir=PROJECT_ROOT / "data")
    ds = loader.load()
    return ds.joined(), ds.users, ds.comments


def load_dataset() -> TicketDataset:
    tickets, users, comments = _load_dataset()
    return TicketDataset(tickets=tickets, users=users, comments=comments)


@dataclass
class FilterState:
    start: date
    end: date
    priorities: list[str]
    categories: list[str]
    agents: list[str]


def render_sidebar_filters(tickets: pd.DataFrame) -> FilterState:
    """Render the global sidebar filters and return the selected state."""
    st.sidebar.header("Filters")
    if tickets.empty:
        today = date.today()
        return FilterState(today, today, [], [], [])

    min_d = tickets["created_at"].min().date()
    max_d = tickets["created_at"].max().date()
    start, end = st.sidebar.date_input(
        "Date range", value=(min_d, max_d), min_value=min_d, max_value=max_d
    )
    priorities = st.sidebar.multiselect(
        "Priority",
        sorted(tickets["priority"].dropna().unique().tolist()),
        default=sorted(tickets["priority"].dropna().unique().tolist()),
    )
    categories = st.sidebar.multiselect(
        "Category",
        sorted(tickets["category"].dropna().unique().tolist()),
        default=[],
        help="Empty = all categories.",
    )
    agents = st.sidebar.multiselect(
        "Agent",
        sorted(tickets["agent_name"].dropna().unique().tolist()),
        default=[],
        help="Empty = all agents.",
    )
    return FilterState(
        start=start,
        end=end,
        priorities=priorities,
        categories=categories,
        agents=agents,
    )


def apply_filters(tickets: pd.DataFrame, f: FilterState) -> pd.DataFrame:
    if tickets.empty:
        return tickets
    df = tickets.copy()
    df = df[
        (df["created_at"].dt.date >= f.start)
        & (df["created_at"].dt.date <= f.end)
    ]
    if f.priorities:
        df = df[df["priority"].isin(f.priorities)]
    if f.categories:
        df = df[df["category"].isin(f.categories)]
    if f.agents:
        df = df[df["agent_name"].isin(f.agents)]
    return df
