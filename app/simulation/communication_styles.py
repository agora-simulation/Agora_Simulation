"""Phase 4: Communication Styles Module.

Generiert sprachliche Stil-Instruktionen basierend auf Alter, Region,
Bildung, B2B/B2C-Kontext und Formalitäts-Level.
Quellen: GGSS/ALLBUS 2023, Stanford Generative Agents.
"""
from typing import Any


# --- Alters-Styles ---

_AGE_STYLES = {
    "gen_z": {
        "range": (18, 25),
        "instruction": (
            "SPRACHSTIL Gen Z: Schreibe in Fragmenten, nicht in ganzen Sätzen. "
            "Nutze Anglizismen (cringe, vibe, lowkey, sus, no cap). "
            "Emojis statt Satzzeichen. Kein Punkt am Ende. Alles kleingeschrieben. "
            "'Digga', 'fr fr', 'ngl'. Selbstironie. Kurz und abgehackt."
        ),
    },
    "millennial": {
        "range": (26, 40),
        "instruction": (
            "SPRACHSTIL Millennial: Mix aus formell und informell. "
            "Gelegentlich 'haha' oder 'lol'. Selbstironie und Sarkasmus. "
            "Grundsätzlich vollständige Sätze, aber locker. "
            "Parenthesen (so wie hier). Gelegentlich ein Emoji."
        ),
    },
    "gen_x": {
        "range": (41, 60),
        "instruction": (
            "SPRACHSTIL Gen X: Direkt und auf den Punkt. Leicht zynisch. "
            "Vollständige Sätze. Wenig Schnörkel. Pragmatisch. "
            "Keine Emojis. Trockener Humor wenn überhaupt."
        ),
    },
    "boomer": {
        "range": (61, 99),
        "instruction": (
            "SPRACHSTIL Boomer: Formell. Grußformeln ('Guten Tag', 'Mit freundlichen Grüßen'). "
            "Auslassungspunkte... überall. Vollständige Sätze mit korrekter Interpunktion. "
            "Höflich aber bestimmt. Keine Abkürzungen. 'MfG' ist das Maximum an Informalität."
        ),
    },
}

# --- Regionale DACH-Styles ---

_REGIONAL_STYLES = {
    "norddeutsch": (
        "DIALEKT Norddeutsch: Trocken, Understatement, knapp. "
        "'Moin'. Wenig Worte, viel Inhalt. 'Nicht schlecht' ist hohes Lob. "
        "'Da kann man nicht meckern'. Sachlich. Keine Übertreibungen."
    ),
    "bayerisch": (
        "DIALEKT Bayerisch: 'Gell', 'des passt scho', 'mei'. "
        "Bodenständig. 'A bisserl' statt 'ein bisschen'. "
        "Gemütlich aber direkt. Gelegentlich bayrische Ausdrücke einfließen lassen."
    ),
    "berlinerisch": (
        "DIALEKT Berlinerisch: 'Dit', 'ick', 'wa'. Direkt bis schnodderig. "
        "'Keen Problem', 'Is mir egal'. Berliner Schnauze: frech aber herzlich. "
        "Kodderschnauze. Keine Angst vor Konfrontation."
    ),
    "oesterreichisch": (
        "DIALEKT Österreichisch: Höflich, Konjunktiv ('Hätten Sie vielleicht...'). "
        "-erl Diminutive: 'Sackerl', 'Busserl'. 'Jänner' statt Januar, "
        "'heuer' statt dieses Jahr. 'Bitte' und 'Danke' inflationär. "
        "'Grüß Gott'. Indirekt und freundlich."
    ),
    "schweizerdeutsch": (
        "DIALEKT Schweizerdeutsch: Kein ß (immer 'ss'). "
        "'Velo' statt Fahrrad, 'Billet' statt Ticket, 'Natel' statt Handy. "
        "'Grüezi', 'merci vilmal'. Indirekt, konsensorientiert. "
        "Understatement. Nie zu direkt oder konfrontativ."
    ),
    "neutral": "",
}

# --- Bildungs-Styles ---

_EDUCATION_STYLES = {
    "Hauptschule": (
        "BILDUNGSNIVEAU Einfach: Kurze, einfache Sätze. Konkret statt abstrakt. "
        "Keine Fremdwörter. Alltagssprache. Dialekt möglich. "
        "Praktische Beispiele statt theoretischer Überlegungen."
    ),
    "Ausbildung": (
        "BILDUNGSNIVEAU Praxis: Klare Sprache, berufsbezogene Fachbegriffe OK. "
        "Pragmatisch. Kurz bis mittel. Direkt. Keine akademischen Floskeln."
    ),
    "Bachelor": (
        "BILDUNGSNIVEAU Mittel: Moderate Komplexität. "
        "Gelegentlich Fachbegriffe. Strukturierte Argumentation. "
        "Nicht zu akademisch, nicht zu einfach."
    ),
    "Master": (
        "BILDUNGSNIVEAU Gehoben: Komplexere Satzstrukturen. "
        "Fachvokabular bei Bedarf. Differenzierte Argumentation. "
        "Gelegentlich Anglizismen aus dem Berufskontext."
    ),
    "Promotion": (
        "BILDUNGSNIVEAU Akademisch: Komplexe Syntax, Nebensätze, Einschübe. "
        "Abstrakte Konzepte. Differenziert und nuanciert. "
        "Präzise Wortwahl. Relativierungen. 'Allerdings', 'Nichtsdestotrotz'."
    ),
}

# --- B2B/B2C-Styles ---

_B2B_STYLES = {
    "b2b": (
        "KONTEXT B2B: Du schreibst aus professioneller Perspektive. "
        "ROI, TCO, Integration, Skalierbarkeit sind deine Themen. "
        "Sachlich, lösungsorientiert. Du bewertest nach Geschäftsnutzen, nicht nach persönlichem Gefühl. "
        "Vergleiche mit Wettbewerbern. Meeting-Sprache."
    ),
    "b2c": "",  # Kein spezieller Stil für B2C (= natürlich)
}

# --- Formalitäts-Levels ---

_FORMALITY_INSTRUCTIONS = {
    1: "FORMALITÄT Sehr salopp: Du/Alter/Digga. Slang. Fragmente. Keine Grammatikregeln.",
    2: "FORMALITÄT Locker: Du-Form. Umgangssprache OK. Kurze Sätze. Informell.",
    3: "FORMALITÄT Normal: Mix. Je nach Situation Sie oder Du. Alltagssprache.",
    4: "FORMALITÄT Formell: Sie-Form bevorzugt. Höflich. Vollständige Sätze. Korrekte Grammatik.",
    5: "FORMALITÄT Sehr formell: Stets Sie. Geschäftssprache. Keine Umgangssprache. Distanziert höflich.",
}


def build_age_style_instruction(age: str) -> str:
    """Gibt Stil-Instruktion basierend auf Alter zurück."""
    try:
        age_num = int(age) if age else 35
    except (ValueError, TypeError):
        age_num = 35

    for style_info in _AGE_STYLES.values():
        low, high = style_info["range"]
        if low <= age_num <= high:
            return style_info["instruction"]

    return _AGE_STYLES["gen_x"]["instruction"]


def build_regional_style_instruction(dialect: str) -> str:
    """Gibt regionale Stil-Instruktion zurück."""
    if not dialect or dialect == "neutral":
        return ""
    return _REGIONAL_STYLES.get(dialect, "")


def build_education_style_instruction(education_level: str) -> str:
    """Gibt bildungsbasierte Stil-Instruktion zurück."""
    if not education_level:
        return ""
    return _EDUCATION_STYLES.get(education_level, "")


def build_b2b_style_instruction(mode: str) -> str:
    """Gibt B2B/B2C Kontext-Instruktion zurück."""
    if not mode:
        return ""
    return _B2B_STYLES.get(mode, "")


def build_formality_instruction(level: int) -> str:
    """Gibt Formalitäts-Instruktion zurück (Level 1-5)."""
    if not level:
        return ""
    return _FORMALITY_INSTRUCTIONS.get(level, _FORMALITY_INSTRUCTIONS[3])


def build_composite_style_prompt(persona: Any) -> str:
    """Kombiniert alle Style-Instruktionen zu einem Gesamt-Prompt.

    Args:
        persona: Persona-Objekt mit age, regional_dialect, education_level,
                 b2b_b2c_mode, formality_level, extra (verbal_tics)

    Returns:
        Kombinierter Style-Prompt-String
    """
    parts = []

    # Alter
    age = getattr(persona, "age", None)
    age_instr = build_age_style_instruction(age)
    if age_instr:
        parts.append(age_instr)

    # Region
    dialect = getattr(persona, "regional_dialect", None)
    region_instr = build_regional_style_instruction(dialect)
    if region_instr:
        parts.append(region_instr)

    # Bildung
    education = getattr(persona, "education_level", None)
    edu_instr = build_education_style_instruction(education)
    if edu_instr:
        parts.append(edu_instr)

    # B2B/B2C
    mode = getattr(persona, "b2b_b2c_mode", None)
    b2b_instr = build_b2b_style_instruction(mode)
    if b2b_instr:
        parts.append(b2b_instr)

    # Formalität
    formality = getattr(persona, "formality_level", None)
    form_instr = build_formality_instruction(formality)
    if form_instr:
        parts.append(form_instr)

    # Verbal Tics aus extra
    extra = getattr(persona, "extra", None) or {}
    verbal_tics = extra.get("verbal_tics", [])
    if verbal_tics:
        tics_str = ", ".join(f'"{t}"' for t in verbal_tics)
        parts.append(
            f"SPRACHMAROTTEN: Verwende regelmäßig diese Füllwörter/Phrasen: {tics_str}. "
            "Baue sie natürlich in deine Sätze ein."
        )

    # Internal Contradictions
    contradictions = extra.get("internal_contradictions", "")
    if contradictions:
        parts.append(
            f"INNERER WIDERSPRUCH: {contradictions} — "
            "Dieser Widerspruch zeigt sich gelegentlich in deinen Posts."
        )

    return "\n\n".join(parts)
