"""Abstract base class for all dashboard metrics."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class Metric(ABC):
    """Common interface for analytics metrics.

    A concrete metric implements :meth:`compute` (pure dataframe-in,
    dataframe-out) and :meth:`render` (Streamlit widgets / Plotly figure).
    Keeping the two concerns separate makes the metrics trivially unit
    testable without any UI dependency.
    """

    title: str = "Metric"
    description: str = ""

    @abstractmethod
    def compute(self, tickets: pd.DataFrame) -> pd.DataFrame:
        """Return the metric's tabular result."""

    @abstractmethod
    def render(self, df: pd.DataFrame, st: Any) -> None:
        """Render the metric into the given Streamlit module."""
