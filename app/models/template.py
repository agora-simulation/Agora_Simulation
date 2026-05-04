"""v1.1: Template-System - 4 Kategorien (research, distribution, tonality, trigger_library)."""
import uuid
from datetime import datetime, timezone

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Template(Base):
    __tablename__ = "templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(String(50), nullable=False)  # research, distribution, tonality, trigger_library
    name = Column(String(255), nullable=False)
    owner_id = Column(String(255), nullable=True)  # NULL = system default
    is_default = Column(Boolean, default=False)
    content = Column(JSON, default=dict)
    version = Column(Integer, default=1)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("templates.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    parent = relationship("Template", remote_side="Template.id")
