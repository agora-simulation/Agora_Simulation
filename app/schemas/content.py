from uuid import UUID
from app.models.content import Platform, ReactionType
from app.schemas.common import UUIDModel, TimestampMixin

class PostRead(UUIDModel, TimestampMixin):
    simulation_id: UUID
    author_id: UUID
    platform: Platform
    content: str
    ingame_day: int
    subreddit: str | None
    author_name: str | None = None
    is_skeptic: bool | None = None

class CommentRead(UUIDModel, TimestampMixin):
    post_id: UUID
    author_id: UUID
    content: str
    ingame_day: int

class ReactionRead(UUIDModel, TimestampMixin):
    post_id: UUID
    persona_id: UUID
    reaction_type: ReactionType
    ingame_day: int

class AnalysisReportRead(UUIDModel, TimestampMixin):
    simulation_id: UUID
    full_report: str
    sentiment_over_time: str | None
    key_turning_points: str | None
    criticism_points: str | None
    opportunities: str | None
    target_segment_analysis: str | None
    unexpected_findings: str | None
    influence_network: str | None = None
    platform_dynamics: str | None = None
    network_evolution: str | None = None
    confidence_assessment: str | None = None
    methodology_limitations: str | None = None

class InfluenceEventRead(UUIDModel, TimestampMixin):
    simulation_id: UUID
    source_persona_id: UUID
    target_persona_id: UUID
    trigger_post_id: UUID | None
    ingame_day: int
    influence_type: str
    description: str | None

class TickRead(UUIDModel, TimestampMixin):
    simulation_id: UUID
    tick_number: int
    ingame_day: int
    snapshot: dict
