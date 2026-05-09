"""Data layer: synthetic generator + loader for the analytics dashboard."""

from data.loader import TicketDataLoader
from data.generator import TicketDataGenerator, SLA_TARGETS_HOURS

__all__ = ["TicketDataLoader", "TicketDataGenerator", "SLA_TARGETS_HOURS"]
