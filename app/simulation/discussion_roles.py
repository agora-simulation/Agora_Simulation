"""Phase 3: Discussion Roles Module.

Weist Diskussionsrollen zu und steuert rollenbasiertes Verhalten
basierend auf Fokusgruppen-Forschung (Focus Agent, Zhang et al. 2024).
"""
import random
from typing import Any

# --- Verteilung aus Fokusgruppen-Forschung ---

DISCUSSION_ROLE_DISTRIBUTION = {
    "opinion_leader": 0.12,
    "engaged": 0.35,
    "follower": 0.30,
    "quiet": 0.15,
    "contrarian": 0.05,
    "showboat": 0.03,
}

# Big-Five-Korrelationen für automatische Zuordnung
_ROLE_BIG_FIVE_PROFILES = {
    "opinion_leader": {"extraversion": (0.7, 1.0), "openness": (0.6, 1.0)},
    "engaged": {"conscientiousness": (0.6, 1.0)},
    "follower": {"agreeableness": (0.7, 1.0)},
    "quiet": {"extraversion": (0.0, 0.3)},
    "contrarian": {"agreeableness": (0.0, 0.3)},
    "showboat": {"extraversion": (0.7, 1.0), "conscientiousness": (0.0, 0.35)},
}

# Rollen-Verhalten
ROLE_BEHAVIORS = {
    "opinion_leader": {
        "post_rate_modifier": 1.5,
        "speaks_first": True,
        "responds_to_majority": False,
        "early_boost_days": 3,
        "early_boost_factor": 1.5,
    },
    "engaged": {
        "post_rate_modifier": 1.0,
        "speaks_first": False,
        "responds_to_majority": False,
        "references_others": True,
    },
    "follower": {
        "post_rate_modifier": 0.7,
        "speaks_first": False,
        "responds_to_majority": True,
        "needs_existing_posts": True,
    },
    "quiet": {
        "post_rate_modifier": 0.2,
        "speaks_first": False,
        "responds_to_majority": False,
        "only_when_addressed": True,
    },
    "contrarian": {
        "post_rate_modifier": 1.0,
        "speaks_first": False,
        "responds_to_majority": False,
        "contradicts_consensus": True,
    },
    "showboat": {
        "post_rate_modifier": 1.3,
        "speaks_first": False,
        "responds_to_majority": False,
        "off_topic_tendency": True,
        "self_referential": True,
    },
}


def assign_discussion_role(persona_data: dict) -> str:
    """Leitet Diskussionsrolle aus Big-Five-Traits ab, mit Zufallskomponente.

    Args:
        persona_data: Dict mit personality_traits (Big Five)

    Returns:
        Rolle als String
    """
    traits = persona_data.get("personality_traits", {})
    if not traits:
        # Fallback: gewichteter Zufall nach Verteilung
        return _random_role_by_distribution()

    # Score jede Rolle basierend auf Big-Five-Match
    scores = {}
    for role, profile in _ROLE_BIG_FIVE_PROFILES.items():
        score = 0.0
        matches = 0
        for trait, (low, high) in profile.items():
            trait_val = traits.get(trait, 0.5)
            if low <= trait_val <= high:
                score += 1.0
                matches += 1
            else:
                # Partielle Punkte für nahe Werte
                distance = min(abs(trait_val - low), abs(trait_val - high))
                score += max(0, 1.0 - distance * 2)
                matches += 1
        scores[role] = score / max(matches, 1)

    # Bester Match mit 60% Wahrscheinlichkeit, sonst gewichteter Zufall
    if random.random() < 0.6:
        best_role = max(scores, key=scores.get)
        return best_role
    else:
        return _random_role_by_distribution()


def _random_role_by_distribution() -> str:
    """Wählt Rolle nach natürlicher Verteilung."""
    roles = list(DISCUSSION_ROLE_DISTRIBUTION.keys())
    weights = list(DISCUSSION_ROLE_DISTRIBUTION.values())
    return random.choices(roles, weights=weights, k=1)[0]


def get_role_behavior_modifier(role: str) -> dict:
    """Gibt Verhaltens-Modifikatoren für eine Rolle zurück."""
    return ROLE_BEHAVIORS.get(role, ROLE_BEHAVIORS["engaged"])


def get_role_prompt_instruction(role: str) -> str:
    """Gibt Prompt-Fragment für das Rollen-Verhalten zurück."""
    instructions = {
        "opinion_leader": (
            "Du bist ein Meinungsführer. Du sprichst ZUERST und rahmst das Thema. "
            "Andere orientieren sich an dir. Sei selbstbewusst und klar in deiner Position. "
            "Du wartest nicht auf andere — du setzt den Ton."
        ),
        "engaged": (
            "Du bist aktiv und engagiert. Du baust auf Beiträge anderer auf, "
            "referenzierst was andere gesagt haben, und bringst die Diskussion weiter. "
            "Du hast eine eigene Meinung, bist aber offen für Argumente."
        ),
        "follower": (
            "Du bist ein Mitläufer. Du stimmst der Mehrheit zu und hältst dich kurz. "
            "'Sehe ich auch so', 'Stimmt'. Du postest nur wenn andere schon gepostet haben. "
            "Du hast selten eine eigene starke Meinung."
        ),
        "quiet": (
            "Du bist sehr still. Du postest fast NIE von dir aus. "
            "Nur wenn du direkt angesprochen wirst oder das Thema dich persönlich betrifft, "
            "schreibst du etwas — und dann kurz."
        ),
        "contrarian": (
            "Du bist ein Querdenker. Du stellst den Konsens IN FRAGE. "
            "Wenn alle dafür sind, bist du dagegen. Wenn alle kritisch sind, verteidigst du. "
            "Du provozierst gerne und spielst den Advocatus Diaboli."
        ),
        "showboat": (
            "Du bist ein Selbstdarsteller. Du redest hauptsächlich über DICH SELBST. "
            "Jedes Thema drehst du so, dass es um deine Erfahrungen geht. "
            "Du schweifst ab, erzählst Anekdoten, und monopolisierst die Aufmerksamkeit."
        ),
    }
    return instructions.get(role, instructions["engaged"])
