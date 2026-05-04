"""v1.1: Platform Layer - formale Plattform-Entität."""
import uuid
from datetime import datetime, timezone

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class SimPlatform(Base):
    __tablename__ = "platforms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id"), nullable=True)  # NULL = global default
    name = Column(String(100), nullable=False)
    character = Column(String(50), nullable=False)  # operativ, institutionell, boulevard, fachlich, oeffentlich
    tonality_modifier = Column(Text, nullable=True)
    reach_multiplier = Column(Float, default=1.0)
    preferred_actor_types = Column(JSON, default=list)
    echo_chamber_strength = Column(Float, default=0.5)
    default_engagement_rate = Column(Float, default=0.3)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)
