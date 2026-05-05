"""Pydantic schemas for the 9 actor types and their profiles, behavior defaults, and templates."""
from enum import Enum
from pydantic import BaseModel, Field


class ActorType(str, Enum):
    private_person = "private_person"
    company = "company"
    research_institute = "research_institute"
    authority = "authority"
    media = "media"
    influencer = "influencer"
    expert = "expert"
    collective = "collective"
    validator = "validator"


class FunctionTag(str, Enum):
    meinungs_gatekeeper = "meinungs_gatekeeper"
    marktzugangs_gatekeeper = "marktzugangs_gatekeeper"
    bruckenakteur = "bruckenakteur"
    multiplikator = "multiplikator"
    polarisierer = "polarisierer"
    early_signal_giver = "early_signal_giver"


class Traegerschaft(str, Enum):
    privat = "privat"
    oeffentlich = "oeffentlich"
    genossenschaftlich = "genossenschaftlich"
    gemischt = "gemischt"
    kommunal = "kommunal"


class PersonContext(str, Enum):
    privat = "privat"
    beruflich = "beruflich"
    oeffentlich = "oeffentlich"


class InfluencerContext(str, Enum):
    consumer = "consumer"
    business = "business"
    politisch = "politisch"


# --- Profile schemas per type ---

class BigFiveTraits(BaseModel):
    openness: float = Field(0.5, ge=0, le=1)
    conscientiousness: float = Field(0.5, ge=0, le=1)
    extraversion: float = Field(0.5, ge=0, le=1)
    agreeableness: float = Field(0.5, ge=0, le=1)
    neuroticism: float = Field(0.5, ge=0, le=1)


class PrivatePersonProfile(BaseModel):
    alter: int = 35
    geschlecht: str = "divers"
    region: str = "Deutschland"
    bildung: str = "Bachelor"
    einkommen: str = "mittel"
    beruf: str | None = None
    rolle: str | None = None
    big_five: BigFiveTraits = BigFiveTraits()
    werte: list[str] = []
    diffusion_phase: str = "early_majority"


class CompanyProfile(BaseModel):
    branche: str = ""
    groesse: str = "mittel"
    marktposition: str = ""
    rechtsform: str = "GmbH"
    risikoaversion: float = Field(0.5, ge=0, le=1)
    markenwerte: list[str] = []
    entscheidungsstruktur: str = "hierarchisch"
    digitalisierungsgrad: float = Field(0.5, ge=0, le=1)


class ResearchInstituteProfile(BaseModel):
    forschungsschwerpunkt: list[str] = []
    reputation: float = Field(0.5, ge=0, le=1)
    finanzierung: str = "oeffentlich"
    publikations_output: str = "mittel"
    kooperationen: list[str] = []


class AuthorityProfile(BaseModel):
    zustaendigkeit: list[str] = []
    hierarchie_ebene: str = "bund"
    politische_ausrichtung: str = "neutral"
    reaktionsgeschwindigkeit: str = "langsam"


class MediaProfile(BaseModel):
    reichweite: int = 100000
    format: str = "online"
    politische_tendenz: float = Field(0.0, ge=-1, le=1)
    zielgruppe: str = ""
    fokus: list[str] = []


class InfluencerProfile(BaseModel):
    plattform: str = "social_media"
    reichweite: int = 10000
    polaritaet: float = Field(0.0, ge=-1, le=1)
    zielgruppe: str = ""
    werbedeals: bool = False
    big_five: BigFiveTraits = BigFiveTraits()


class ExpertProfile(BaseModel):
    domaene: str = ""
    jahre_erfahrung: int = 10
    sichtbarkeit: float = Field(0.5, ge=0, le=1)
    affiliation: str = ""
    affiliation_type: str = "freelance"
    big_five: BigFiveTraits = BigFiveTraits()


class CollectiveProfile(BaseModel):
    mitgliederzahl: int = 1000
    mandat: str = ""
    lobbyaktivitaet: str = "mittel"
    politische_verortung: float = Field(0.0, ge=-1, le=1)
    reichweite_in_branche: float = Field(0.5, ge=0, le=1)


class ValidatorProfile(BaseModel):
    pruefdomaene: list[str] = []
    autoritaet_in_domaene: float = Field(0.8, ge=0, le=1)
    reaktionsgeschwindigkeit: str = "langsam"
    freigabe_status: str = "pending"
    freigabe_begruendung: str | None = None


# --- Actor behavior defaults ---

class ActorBehaviorDefaults(BaseModel):
    posts_per_tick: float
    activation_latency_min: int
    activation_latency_max: int
    trigger_threshold: int | None
    reach_multiplier_min: float
    reach_multiplier_max: float
    credibility: float
    dropout_rate: float
    engagement_decay_rate: float


ACTOR_BEHAVIOR_DEFAULTS: dict[str, ActorBehaviorDefaults] = {
    "private_person": ActorBehaviorDefaults(posts_per_tick=0.3, activation_latency_min=0, activation_latency_max=1, trigger_threshold=None, reach_multiplier_min=1, reach_multiplier_max=1, credibility=0.5, dropout_rate=0.3, engagement_decay_rate=0.1),
    "company": ActorBehaviorDefaults(posts_per_tick=0.1, activation_latency_min=1, activation_latency_max=3, trigger_threshold=None, reach_multiplier_min=5, reach_multiplier_max=20, credibility=0.6, dropout_rate=0.1, engagement_decay_rate=0.05),
    "research_institute": ActorBehaviorDefaults(posts_per_tick=0.05, activation_latency_min=5, activation_latency_max=10, trigger_threshold=2000, reach_multiplier_min=10, reach_multiplier_max=30, credibility=0.9, dropout_rate=0.05, engagement_decay_rate=0.03),
    "authority": ActorBehaviorDefaults(posts_per_tick=0.02, activation_latency_min=7, activation_latency_max=15, trigger_threshold=5000, reach_multiplier_min=30, reach_multiplier_max=100, credibility=0.85, dropout_rate=0.05, engagement_decay_rate=0.02),
    "media": ActorBehaviorDefaults(posts_per_tick=0.4, activation_latency_min=1, activation_latency_max=4, trigger_threshold=500, reach_multiplier_min=50, reach_multiplier_max=500, credibility=0.7, dropout_rate=0.05, engagement_decay_rate=0.08),
    "influencer": ActorBehaviorDefaults(posts_per_tick=0.6, activation_latency_min=0, activation_latency_max=2, trigger_threshold=None, reach_multiplier_min=100, reach_multiplier_max=1000, credibility=0.6, dropout_rate=0.05, engagement_decay_rate=0.1),
    "expert": ActorBehaviorDefaults(posts_per_tick=0.2, activation_latency_min=2, activation_latency_max=5, trigger_threshold=1000, reach_multiplier_min=5, reach_multiplier_max=50, credibility=0.85, dropout_rate=0.1, engagement_decay_rate=0.05),
    "collective": ActorBehaviorDefaults(posts_per_tick=0.15, activation_latency_min=3, activation_latency_max=7, trigger_threshold=3000, reach_multiplier_min=20, reach_multiplier_max=200, credibility=0.6, dropout_rate=0.08, engagement_decay_rate=0.04),
    "validator": ActorBehaviorDefaults(posts_per_tick=0.01, activation_latency_min=10, activation_latency_max=20, trigger_threshold=None, reach_multiplier_min=30, reach_multiplier_max=100, credibility=0.95, dropout_rate=0.02, engagement_decay_rate=0.01),
}


# --- Distribution templates ---

DISTRIBUTION_TEMPLATES: dict[str, dict[str, float]] = {
    "b2c_konsum": {"private_person": 75, "company": 5, "research_institute": 0, "authority": 2, "media": 5, "influencer": 8, "expert": 3, "collective": 2, "validator": 0},
    "b2b_software": {"private_person": 10, "company": 50, "research_institute": 5, "authority": 5, "media": 5, "influencer": 5, "expert": 12, "collective": 5, "validator": 3},
    "b2b_industriegut": {"private_person": 10, "company": 40, "research_institute": 5, "authority": 8, "media": 5, "influencer": 3, "expert": 15, "collective": 7, "validator": 7},
    "forschungskampagne": {"private_person": 5, "company": 22, "research_institute": 35, "authority": 15, "media": 10, "influencer": 0, "expert": 8, "collective": 3, "validator": 2},
    "politische_initiative": {"private_person": 30, "company": 5, "research_institute": 5, "authority": 15, "media": 23, "influencer": 5, "expert": 5, "collective": 10, "validator": 2},
    "healthcare_pharma": {"private_person": 22, "company": 13, "research_institute": 20, "authority": 13, "media": 10, "influencer": 5, "expert": 8, "collective": 4, "validator": 5},
    "finanz": {"private_person": 28, "company": 22, "research_institute": 5, "authority": 13, "media": 10, "influencer": 5, "expert": 8, "collective": 4, "validator": 5},
}


# --- Szenario-Respondenten-Mix (Realism Overhaul Phase 7) ---
# Szenario-spezifische Verteilungen auf Basis von Marktforschungsmethodik

SCENARIO_RESPONDENT_MIX: dict[str, dict[str, int]] = {
    "b2c_product": {
        "private_person": 75, "influencer": 12, "company": 8, "expert": 5,
    },
    "b2b_saas": {
        "company": 35, "expert": 28, "private_person": 22, "authority": 15,
    },
    "healthcare": {
        "expert": 45, "authority": 18, "research_institute": 12,
        "private_person": 8, "company": 17,
    },
    "political": {
        "private_person": 70, "media": 10, "expert": 8,
        "collective": 5, "authority": 5, "influencer": 2,
    },
    "financial": {
        "private_person": 45, "company": 22, "expert": 18, "authority": 15,
    },
    "industrial": {
        "company": 28, "expert": 28, "authority": 17,
        "private_person": 12, "research_institute": 15,
    },
}


def resolve_scenario_to_actor_distribution(scenario_type: str) -> dict[str, int]:
    """Löst einen Szenario-Typ in eine Akteurs-Verteilung auf.

    Falls der Szenario-Typ nicht in SCENARIO_RESPONDENT_MIX vorhanden ist,
    wird auf DISTRIBUTION_TEMPLATES zurückgefallen.

    Args:
        scenario_type: z.B. "b2c_product", "b2b_saas", "healthcare"

    Returns:
        Dict mit Akteurs-Typ -> Prozent-Anteil
    """
    if scenario_type in SCENARIO_RESPONDENT_MIX:
        return SCENARIO_RESPONDENT_MIX[scenario_type]

    # Mapping Szenario -> existierendes Template
    _SCENARIO_TO_TEMPLATE = {
        "b2c_product": "b2c_konsum",
        "b2b_saas": "b2b_software",
        "healthcare": "healthcare_pharma",
        "political": "politische_initiative",
        "financial": "finanz",
        "industrial": "b2b_industriegut",
    }
    template_key = _SCENARIO_TO_TEMPLATE.get(scenario_type, "b2c_konsum")
    return DISTRIBUTION_TEMPLATES.get(template_key, DISTRIBUTION_TEMPLATES["b2c_konsum"])


# --- Platform affinity defaults ---

PLATFORM_AFFINITY_DEFAULTS: dict[str, dict[str, float]] = {
    "private_person_privat": {"threadit": 0.4, "feedbook": 0.2, "newsfeed": 0.8, "fachforum": 0.1},
    "private_person_beruflich": {"threadit": 0.8, "feedbook": 0.4, "newsfeed": 0.2, "fachforum": 0.7},
    "company": {"threadit": 0.7, "feedbook": 0.7, "newsfeed": 0.2, "fachforum": 0.5},
    "research_institute": {"threadit": 0.3, "feedbook": 0.6, "newsfeed": 0.2, "fachforum": 0.8},
    "authority": {"threadit": 0.2, "feedbook": 0.8, "newsfeed": 0.4, "fachforum": 0.3},
    "media": {"threadit": 0.5, "feedbook": 0.5, "newsfeed": 0.8, "fachforum": 0.2},
    "influencer": {"threadit": 0.7, "feedbook": 0.2, "newsfeed": 0.8, "fachforum": 0.2},
    "expert": {"threadit": 0.7, "feedbook": 0.4, "newsfeed": 0.2, "fachforum": 0.8},
    "collective": {"threadit": 0.4, "feedbook": 0.7, "newsfeed": 0.4, "fachforum": 0.3},
    "validator": {"threadit": 0.2, "feedbook": 0.7, "newsfeed": 0.2, "fachforum": 0.8},
}


# --- Tonality templates per actor type ---

TONALITY_TEMPLATES: dict[str, str] = {
    "private_person": "Spricht aus persoenlicher Erfahrung, emotional, direkt. Verwendet Alltagssprache.",
    "company": "Offiziell, vorsichtig formuliert, markenkonform. Vermeidet kontroverse Aussagen.",
    "research_institute": "Evidenzbasiert, zurueckhaltend, differenziert. Zitiert Studien und Daten.",
    "authority": "Formal, regelorientiert, sachlich. Verwendet Amtssprache und Verordnungs-Terminologie.",
    "media": "Neutral-skeptisch, story-orientiert, recherchiert. Sucht Kontraste und Zitate.",
    "influencer": "Persoenlich, polarisierend, engagement-orientiert. Verwendet Emojis und direkte Ansprache.",
    "expert": "Sachlich, fachterminologisch, themengebunden. Argumentiert mit Domaenenwissen.",
    "collective": "Vertritt Gruppeninteresse, mobilisierend, politisch gefaerbt. Fordert zum Handeln auf.",
    "validator": "Formal-technisch, pruefend, binaer. Gibt Freigabe oder Ablehnung mit Begruendung.",
}
