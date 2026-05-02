"""
MarketContext: Speichert das Ergebnis der Web-Recherche vor der Simulation.
Strukturiert in drei Schichten: Makro, Branche, Zielgruppe.
"""
import uuid
from datetime import datetime, timezone


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class MarketContext(Base):
    __tablename__ = "market_contexts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id"), nullable=False, unique=True)

    # Drei Recherche-Schichten (jeweils Markdown-Text)
    macro_context = Column(Text, nullable=True)        # Wirtschaft, Politik, Gesellschaft
    industry_context = Column(Text, nullable=True)      # Branche, Wettbewerb, Regulierung
    target_group_context = Column(Text, nullable=True)  # Zielgruppe, Trends, Schmerzpunkte

    # Rohdaten der Recherche (JSON mit Quellen + Snippets)
    raw_sources = Column(JSON, nullable=True)

    # Kompakte Zusammenfassung für Prompt-Injection (max ~500 Wörter)
    prompt_summary = Column(Text, nullable=True)

    # Meta
    research_queries = Column(JSON, nullable=True)  # Welche Suchbegriffe verwendet wurden
    research_mode = Column(String(10), default="deep")
    created_at = Column(DateTime, default=_utcnow)

    simulation = relationship("Simulation", back_populates="market_context")
