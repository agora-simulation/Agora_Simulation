"""Phase 2: Response Calibration Module.

Kalibriert Antwort-Typen, Längen und Fatigue basierend auf
Marktforschungs-Erkenntnissen (AAPOR, PMC Survey Fatigue, Drive Research).
"""
import random
from typing import Any

# --- Konstanten aus Marktforschung ---

RESPONSE_LENGTH_DISTRIBUTION = {"one_liner": 0.35, "medium": 0.40, "detailed": 0.25}
NOISE_RATE = 0.20          # 15-30% in echten Studien
SUPERFICIAL_RATE = 0.25    # 20-30% oberflächlich
PROTEST_RATE = 0.05        # 3-8% Protest
ACQUIESCENCE_RATE = 0.15   # 10-20% Ja-Sager
FATIGUE_CURVE = lambda tick, total: min(1.0, 0.3 * (tick / total)) if total > 0 else 0.0


def determine_response_type(persona: Any, tick: int, total_ticks: int) -> str:
    """Bestimmt den Response-Typ basierend auf Persona-Traits + Zufall.

    Returns: normal, noise, protest, acquiescence, superficial
    """
    fatigue = calculate_fatigue_modifier(persona, tick, total_ticks)
    noise_prop = getattr(persona, "noise_propensity", None) or 0.15
    acq_bias = getattr(persona, "acquiescence_bias", None) or 0.10
    fatigue_rate = getattr(persona, "survey_fatigue_rate", None) or 0.20

    roll = random.random()

    # Fatigue erhöht alle "schlechten" Response-Typen
    fatigue_boost = fatigue * fatigue_rate

    # Protest (selten, aber steigt mit Fatigue)
    protest_threshold = PROTEST_RATE + fatigue_boost * 0.5
    if roll < protest_threshold:
        return "protest"

    # Noise/Off-Topic
    noise_threshold = protest_threshold + noise_prop * (1 + fatigue_boost)
    if roll < noise_threshold:
        return "noise"

    # Acquiescence (Ja-Sager)
    acq_threshold = noise_threshold + acq_bias * (1 + fatigue_boost * 0.3)
    if roll < acq_threshold:
        return "acquiescence"

    # Superficial (oberflächlich, steigt stark mit Fatigue)
    superficial_threshold = acq_threshold + SUPERFICIAL_RATE * fatigue
    if roll < superficial_threshold:
        return "superficial"

    return "normal"


def determine_response_length(persona: Any) -> str:
    """Bestimmt Antwort-Länge basierend auf Persona-Tendenz mit Varianz.

    Returns: one_liner, medium, detailed
    """
    tendency = getattr(persona, "response_length_tendency", None) or "medium"

    # Tendenz als Gewichtung verwenden, aber mit Zufallskomponente
    weights = dict(RESPONSE_LENGTH_DISTRIBUTION)

    # Persona-Tendenz verstärken (+30%)
    if tendency in weights:
        weights[tendency] *= 1.3

    # Normalisieren
    total = sum(weights.values())
    choices = list(weights.keys())
    probs = [weights[c] / total for c in choices]

    return random.choices(choices, weights=probs, k=1)[0]


def build_length_instruction(length_type: str) -> str:
    """Gibt Prompt-Instruktion für die Antwort-Länge zurück."""
    instructions = {
        "one_liner": "Antworte in MAXIMAL 1-2 Sätzen. Oft reicht ein Wort oder ein Fragment.",
        "medium": "Antworte in 2-3 Sätzen.",
        "detailed": "Antworte ausführlich, 4-8 Sätze. Gehe ins Detail.",
    }
    return instructions.get(length_type, instructions["medium"])


def build_noise_instruction(response_type: str) -> str:
    """Gibt Prompt-Instruktion für den Response-Typ zurück.

    Nur für nicht-normale Typen relevant.
    """
    instructions = {
        "noise": (
            "Du bist heute abgelenkt. Schreibe etwas Off-Topic — "
            "erzähle von deinem Tag, beschwere dich über etwas Unrelated, "
            "oder schweife ab. Beziehe dich NICHT auf das eigentliche Thema."
        ),
        "protest": (
            "Du bist frustriert und genervt. Alles ist Mist. "
            "Schreibe eine kurze, abwertende Antwort. "
            "'Was soll der Scheiß', 'Interessiert mich nicht', 'Alles Verarsche'."
        ),
        "acquiescence": (
            "Du stimmst heute allem zu, egal was. "
            "'Ja stimmt', 'Sehe ich auch so', 'Guter Punkt'. "
            "Du hast keine eigene Meinung, du folgst dem Mainstream."
        ),
        "superficial": (
            "Du hast absolut keine Lust. "
            "Antworte in MAXIMAL 3-4 Wörtern. 'Ja', 'Nö', 'Weiß nicht', 'Egal'."
        ),
    }
    return instructions.get(response_type, "")


def calculate_fatigue_modifier(persona: Any, tick: int, total_ticks: int) -> float:
    """Berechnet Qualitäts-Degradation durch Survey Fatigue.

    Returns: 0.0 (keine Ermüdung) bis 1.0 (maximal ermüdet)
    """
    if total_ticks <= 0:
        return 0.0

    fatigue_rate = getattr(persona, "survey_fatigue_rate", None) or 0.20
    base_fatigue = FATIGUE_CURVE(tick, total_ticks)

    # Persona-spezifische Rate moduliert die Kurve
    return min(1.0, base_fatigue * (fatigue_rate / 0.20))
