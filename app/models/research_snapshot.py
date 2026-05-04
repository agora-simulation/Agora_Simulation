"""v1.1: Research Snapshots - eigenstaendige Marktrecherchen."""
import uuid
from datetime import datetime, timezone

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

from sqlalchemy import Column, DateTime, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class ResearchSnapshot(Base):
    __tablename__ = "research_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    owner_id = Column(String(255), nullable=True)  # API key or user identifier
    llm_used = Column(String(100), nullable=True)
    passes = Column(JSON, default={})  # {markt: {content, sources, confidence}, sozio_kultur: {...}, ...}
    status = Column(String(20), default="draft")  # draft, approved, archived
    suggested_triggers = Column(JSON, default=[])  # trigger events suggested from research
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
