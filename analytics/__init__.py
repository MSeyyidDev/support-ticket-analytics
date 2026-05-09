"""Metric classes that power the dashboard.

Each metric exposes the same surface area::

    metric = SomeMetric()
    df = metric.compute(tickets_df)
    metric.render(df, st)  # streams Streamlit widgets

This keeps the dashboard pages tiny and the metrics independently testable.
"""

from analytics.base import Metric
from analytics.tickets_per_day import TicketsPerDayMetric
from analytics.resolution_time import ResolutionTimeMetric
from analytics.priority_distribution import PriorityDistributionMetric
from analytics.category_frequency import CategoryFrequencyMetric
from analytics.sla_breach import SLABreachMetric
from analytics.open_by_agent import OpenByAgentMetric
from analytics.backlog_trend import BacklogTrendMetric
from analytics.first_response_time import FirstResponseTimeMetric

__all__ = [
    "Metric",
    "TicketsPerDayMetric",
    "ResolutionTimeMetric",
    "PriorityDistributionMetric",
    "CategoryFrequencyMetric",
    "SLABreachMetric",
    "OpenByAgentMetric",
    "BacklogTrendMetric",
    "FirstResponseTimeMetric",
]
