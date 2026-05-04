from uuid import UUID
from app.schemas.common import UUIDModel, TimestampMixin


class PersonaRead(UUIDModel, TimestampMixin):
    simulation_id: UUID
    name: str
    age: str | None
    location: str | None
    occupation: str | None
    personality: str | None
    values: list[str]
    communication_style: str | None
    initial_opinion: str | None
    is_skeptic: bool
    persona_type: str = "individual"
    entity_subtype: str | None = None
    current_state: dict
    social_connections: list
    # Modul 1: Langzeitgedächtnis
    memory: list[dict] = []
    # Modul 3: Erweiterte Felder
    education_level: str | None = None
    income_bracket: str | None = None
    family_status: str | None = None
    political_leaning: str | None = None
    media_consumption: list[str] = []
    tech_affinity: float | None = None
    personality_traits: dict = {}
    # v1.1: Actor System
    actor_type: str = "private_person"
    subtype: str | None = None
    context: str | None = None
    traegerschaft: str | None = None
    stance: str | None = None
    activation_latency: int = 0
    trigger_condition: dict | None = None
    function_tags: list[str] = []
    engagement_decay_rate: float = 0.05
    profile_data: dict = {}
