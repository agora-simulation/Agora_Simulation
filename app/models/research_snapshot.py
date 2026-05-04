"""v1.1: Research Snapshots - eigenstaendige Marktrecherchen."""
import uuid
from datetime import datetime, timezone

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class ResearchSnapshot(Base):
    __tablename__ = "research_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    owner_id = Column(String(255), nullable=True)
    llm_used = Column(String(100), nullable=True)
    passes = Column(JSON, default=dict)
    status = Column(String(20), default="draft")  # draft, running, completed, approved, archived, failed
    suggested_triggers = Column(JSON, default=list)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # --- v1.2: Research execution fields ---
    provider_id = Column(UUID(as_uuid=True), ForeignKey("llm_providers.id", ondelete="SET NULL"), nullable=True)
    model = Column(String(100), nullable=True)
    prompt = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("templates.id", ondelete="SET NULL"), nullable=True)
    temperature = Column(Float, nullable=True)
    max_tokens = Column(Integer, default=4096)
    execution_started_at = Column(DateTime, nullable=True)
    execution_finished_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
