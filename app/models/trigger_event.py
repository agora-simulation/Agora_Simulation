"""v1.1: Trigger Events - News-Injection und automatische Events."""
import uuid
from datetime import datetime, timezone

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class TriggerEvent(Base):
    __tablename__ = "trigger_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id"), nullable=False)
    tick_day = Column(Integer, nullable=False)
    event_type = Column(String(50), nullable=False)  # news_headline, competitor_action, regulatory_change, validator_decision, social_incident
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    affected_segments = Column(JSON, default=list)  # which actor types react
    intensity = Column(String(20), default="minor")  # minor, major, critical
    source_attribution = Column(String(500), nullable=True)
    was_auto_generated = Column(Boolean, default=False)  # for stagnation auto-reactivation
    created_at = Column(DateTime, default=_utcnow)

    simulation = relationship("Simulation", backref="trigger_events")
