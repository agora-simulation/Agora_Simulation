import uuid
from datetime import datetime, timezone


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Persona(Base):
    __tablename__ = "personas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    age = Column(String(50))
    location = Column(String(255))       # z.B. "München", "Berlin", "Wien"
    occupation = Column(String(255))
    personality = Column(Text)           # Ausführliche Persönlichkeitsbeschreibung
    values = Column(JSON, default=[])    # Kernwerte als Liste
    communication_style = Column(Text)   # Wie schreibt/spricht diese Person?
    initial_opinion = Column(Text)       # Erste Haltung zum Produkt
    is_skeptic = Column(Boolean, default=False)
    persona_type = Column(String(50), default="individual")  # individual, organization, institution, politician
    entity_subtype = Column(String(200))  # z.B. "tech_startup", "forschungsinstitut"
    social_connections = Column(JSON, default=[])  # UUIDs verbundener Personas

    # Modul 1: Langzeitgedächtnis
    # Struktur: [{"tick": int, "type": str, "summary": str, "emotional_weight": float, ...}]
    memory = Column(JSON, default=[])

    # Modul 3: Erweiterte Felder — Demografie
    education_level = Column(String(50))    # "Hauptschule", "Ausbildung", "Bachelor", "Master", "Promotion"
    income_bracket = Column(String(50))     # "niedrig", "mittel", "hoch", "sehr_hoch"
    family_status = Column(String(100))     # "single", "partnerschaft", "familie_klein", etc.
    political_leaning = Column(String(100)) # "links", "mitte", "rechts", "unpolitisch", etc.
    media_consumption = Column(JSON, default=[])  # ["social_media", "qualitaetspresse", ...]
    tech_affinity = Column(Float, default=0.5)    # 0.0 (technikfern) bis 1.0 (early adopter)

    # Modul 3: Big-Five-Persönlichkeitsmodell
    # Struktur: {"openness": float, "conscientiousness": float, "extraversion": float,
    #            "agreeableness": float, "neuroticism": float}
    personality_traits = Column(JSON, default={})

    # JSON-Struktur:
    # {
    #   "opinion_evolution": str,          — Meinungsentwicklung (kumulativ)
    #   "mood": str,                        — Aktuelle Stimmung (ein Wort)
    #   "recent_actions": [...],            — Ringpuffer (max 5)
    #   "platform_affinity": {"feedbook": float, "threadit": float},
    #   "connection_strength": {persona_id: float, ...},
    #   "opinion_dimensions": {            — Modul 2: Mehrdimensionale Meinung
    #     "product_quality": float,        — -1.0 bis +1.0
    #     "price_fairness": float,
    #     "brand_trust": float,
    #     "innovation": float,
    #     "ethical_concerns": float,
    #     "social_proof": float,
    #     "personal_relevance": float
    #   }
    # }
    current_state = Column(JSON, default={})
    extra = Column(JSON, default={})     # Sonstige Attribute

    # v1.1: Actor System
    actor_type = Column(String(50), nullable=False, default="private_person")  # 9 types
    subtype = Column(String(100), nullable=True)  # for collective/validator subtypes
    context = Column(String(50), nullable=True)  # for private_person/influencer
    traegerschaft = Column(String(50), nullable=True)  # for org types
    stance = Column(String(100), nullable=True)  # type-specific stance
    activation_latency = Column(Integer, nullable=False, default=0)  # days before active
    trigger_condition = Column(JSON, nullable=True)  # threshold conditions
    function_tags = Column(JSON, default=[])  # meinungs_gatekeeper, bruckenakteur etc.
    engagement_decay_rate = Column(Float, default=0.05)
    profile_data = Column(JSON, default={})  # type-specific profile fields

    created_at = Column(DateTime, default=_utcnow)

    simulation = relationship("Simulation", back_populates="personas")
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    reactions = relationship("Reaction", back_populates="persona", cascade="all, delete-orphan")
    conversations = relationship("PersonaConversation", back_populates="persona", cascade="all, delete-orphan")
    # v1.1 relationships
    outgoing_relationships = relationship("ActorRelationship", foreign_keys="ActorRelationship.source_persona_id", back_populates="source_persona", cascade="all, delete-orphan")
    incoming_relationships = relationship("ActorRelationship", foreign_keys="ActorRelationship.target_persona_id", back_populates="target_persona", cascade="all, delete-orphan")
    validator_decisions = relationship("ValidatorDecision", back_populates="validator_persona", cascade="all, delete-orphan")
