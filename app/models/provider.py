import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class LLMProviderRegistry(Base):
    """Globale Provider-Registry: Anthropic, OpenAI, Ollama etc."""

    __tablename__ = "llm_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)                    # Display-Name, z.B. "Mein Anthropic"
    provider_type = Column(String(32), nullable=False)            # "anthropic" | "openai" | "ollama"
    api_key_encrypted = Column(String(2048), nullable=False)      # Fernet-verschlüsselt
    base_url = Column(String(2048), nullable=True)                # Custom URL für Ollama / Azure
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
