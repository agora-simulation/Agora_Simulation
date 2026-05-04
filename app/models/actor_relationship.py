"""v1.1: Actor Relationships - a-priori Beziehungen zwischen Personas."""
import uuid
from datetime import datetime, timezone

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

from sqlalchemy import Column, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ActorRelationship(Base):
    __tablename__ = "actor_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
    target_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String(50), nullable=False)  # kennt, vertraut, konkurriert, zitiert, kaskadiert_von
    weight = Column(Float, default=1.0)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id"), nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    source_persona = relationship("Persona", foreign_keys=[source_persona_id], back_populates="outgoing_relationships")
    target_persona = relationship("Persona", foreign_keys=[target_persona_id], back_populates="incoming_relationships")
    simulation = relationship("Simulation")
