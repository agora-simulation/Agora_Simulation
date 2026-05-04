import uuid
from datetime import datetime, timezone


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class SimulationStatus(str, PyEnum):
    pending = "pending"
    researching = "researching"
    research_complete = "research_complete"
    running = "running"
    completed = "completed"
    failed = "failed"


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    product_description = Column(Text, nullable=False)
    target_market = Column(String(255))
    industry = Column(String(255))
    status = Column(Enum(SimulationStatus, name='simulationstatus', create_type=False), default=SimulationStatus.pending, nullable=False)
    config = Column(JSON, default={})  # persona_count, tick_count, tick_duration_days
    current_tick = Column(Integer, default=0)
    total_ticks = Column(Integer, default=15)
    webhook_url = Column(String(2048), nullable=True)   # Optional: URL für Completion-Notification
    llm_provider = Column(String(32), nullable=False, default="anthropic")   # "anthropic" | "openai"
    llm_model_fast = Column(String(64), nullable=True)    # Optional Override für Fast-Tier (Aktionen/State)
    llm_model_smart = Column(String(64), nullable=True)   # Optional Override für Smart-Tier (Persona-Gen/Report/Chat)
    provider_config = Column(JSON, nullable=True)         # Neue granulare Provider-Config (überschreibt llm_provider wenn gesetzt)
    run_group_id = Column(UUID(as_uuid=True), nullable=True, index=True)   # Multi-Run: Gruppen-ID für zusammengehörige Runs
    run_index = Column(Integer, nullable=True)              # Multi-Run: 0-basierter Index innerhalb der Gruppe
    research_mode = Column(String(10), nullable=False, default="quick")  # "quick" | "deep"
    # v1.1
    research_snapshot_id = Column(UUID(as_uuid=True), ForeignKey("research_snapshots.id"), nullable=True)
    stagnation_mode = Column(String(20), default="mild")  # off, mild, aggressive
    distribution_template = Column(JSON, nullable=True)  # actor type distribution percentages
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    personas = relationship("Persona", back_populates="simulation", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="simulation", cascade="all, delete-orphan")
    ticks = relationship("SimulationTick", back_populates="simulation", cascade="all, delete-orphan")
    reports = relationship("AnalysisReport", back_populates="simulation", cascade="all, delete-orphan")
    market_context = relationship("MarketContext", back_populates="simulation", uselist=False, cascade="all, delete-orphan")
    research_snapshot = relationship("ResearchSnapshot", foreign_keys=[research_snapshot_id])


class SimulationTick(Base):
    __tablename__ = "simulation_ticks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id"), nullable=False)
    tick_number = Column(Integer, nullable=False)
    ingame_day = Column(Integer, nullable=False)
    snapshot = Column(JSON, default={})  # Weltstand-Snapshot des Ticks
    created_at = Column(DateTime, default=_utcnow)

    simulation = relationship("Simulation", back_populates="ticks")
