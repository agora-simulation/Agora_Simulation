"""v1.1: Validator Decisions - binaere Signale von Validierern/Zertifizierern."""
import uuid
from datetime import datetime, timezone

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ValidatorDecision(Base):
    __tablename__ = "validator_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    validator_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id"), nullable=False)
    tick_day = Column(Integer, nullable=False)
    freigabe_status = Column(String(20), nullable=False)  # pending, approved, rejected, conditional
    freigabe_begruendung = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    validator_persona = relationship("Persona", back_populates="validator_decisions")
    simulation = relationship("Simulation")
