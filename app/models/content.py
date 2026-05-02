import uuid
from datetime import datetime, timezone


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Platform(str, PyEnum):
    feedbook = "feedbook"   # Facebook-ähnlich
    threadit = "threadit"   # Reddit-ähnlich


class ReactionType(str, PyEnum):
    like = "like"
    dislike = "dislike"
    share = "share"


class Post(Base):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    platform = Column(Enum(Platform, name='platform', create_type=False), nullable=False)
    content = Column(Text, nullable=False)
    ingame_day = Column(Integer, nullable=False)   # Simulierter Zeitpunkt
    subreddit = Column(String(255))                # Nur für Threadit
    created_at = Column(DateTime, default=_utcnow)

    simulation = relationship("Simulation", back_populates="posts")
    author = relationship("Persona", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    reactions = relationship("Reaction", back_populates="post", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    content = Column(Text, nullable=False)
    ingame_day = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    post = relationship("Post", back_populates="comments")
    author = relationship("Persona", back_populates="comments")


class Reaction(Base):
    __tablename__ = "reactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    reaction_type = Column(Enum(ReactionType, name='reactiontype', create_type=False), nullable=False)
    ingame_day = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    post = relationship("Post", back_populates="reactions")
    persona = relationship("Persona", back_populates="reactions")


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id"), nullable=False)
    sentiment_over_time = Column(Text)   # JSON als Text (Verlauf)
    key_turning_points = Column(Text)
    criticism_points = Column(Text)
    opportunities = Column(Text)
    target_segment_analysis = Column(Text)
    unexpected_findings = Column(Text)
    full_report = Column(Text)           # Kompletter Sonnet-generierter Report
    influence_network = Column(Text)     # Influence-Netzwerk-Analyse
    platform_dynamics = Column(Text)     # Plattform-Analyse (FeedBook vs Threadit)
    network_evolution = Column(Text)     # Netzwerk-Dynamik (Communities, Echokammern)
    confidence_assessment = Column(Text)  # Konfidenz-Bewertung pro Erkenntnis
    methodology_limitations = Column(Text)  # Was die Simulation NICHT leisten kann
    created_at = Column(DateTime, default=_utcnow)

    simulation = relationship("Simulation", back_populates="reports")


class InfluenceEvent(Base):
    __tablename__ = "influence_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id"), nullable=False)
    source_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)  # Wer hat beeinflusst
    target_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)  # Wer wurde beeinflusst
    trigger_post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=True)        # Welcher Post war der Auslöser
    ingame_day = Column(Integer, nullable=False)
    influence_type = Column(String(50), nullable=False)  # "opinion_shift", "mood_change", "engagement"
    description = Column(Text)                           # Kurzbeschreibung was passiert ist
    created_at = Column(DateTime, default=_utcnow)

    simulation = relationship("Simulation")
    source_persona = relationship("Persona", foreign_keys=[source_persona_id])
    target_persona = relationship("Persona", foreign_keys=[target_persona_id])
    trigger_post = relationship("Post")
