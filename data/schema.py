"""Schema definitions for the synthetic ticket dataset.

The schema is intentionally compatible with a typical IT-support ticketing
backend (think Jira Service Management / Zendesk / a generic
``ticket-system-api``) so that the loader can be swapped out for a live API
without touching the analytics layer.
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(160), nullable=False, unique=True)
    role = Column(String(20), nullable=False)  # 'agent' | 'requester'
    department = Column(String(60), nullable=False)
    created_at = Column(DateTime, nullable=False)


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), nullable=False)  # open|in_progress|resolved|closed
    priority = Column(String(20), nullable=False)  # critical|high|medium|low
    category = Column(String(40), nullable=False)
    tags = Column(String(200), nullable=False, default="")
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    first_response_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    sla_target_hours = Column(Integer, nullable=False)

    requester = relationship("User", foreign_keys=[requester_id])
    agent = relationship("User", foreign_keys=[agent_id])
    comments = relationship("Comment", back_populates="ticket")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)

    ticket = relationship("Ticket", back_populates="comments")


def create_schema(database_url: str):
    """Create an engine with all tables materialised."""
    engine = create_engine(database_url, future=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return engine
