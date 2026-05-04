"""v1.1: Crowd Layer - statistisches Aggregat pro Plattform/Tick."""
import uuid
from datetime import datetime, timezone

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class CrowdState(Base):
    __tablename__ = "crowd_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id"), nullable=False)
    platform_id = Column(UUID(as_uuid=True), ForeignKey("platforms.id"), nullable=True)
    tick = Column(Integer, nullable=False)
    volume = Column(Integer, default=0)
    sentiment = Column(Float, default=0.0)  # -1 to +1
    polarization = Column(Float, default=0.0)  # 0 to 1
    momentum = Column(Float, default=0.0)
    representative_voices = Column(JSON, default=list)
    created_at = Column(DateTime, default=_utcnow)

    simulation = relationship("Simulation", backref="crowd_states")
