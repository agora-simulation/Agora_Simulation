# Implementierungsplan: Persona-Realismus-Upgrade

> **Ziel:** Maximale Realitaetstreue der Simulation durch tiefere Persona-Psychologie,  
> persistentes Gedaechtnis und dynamische Meinungsbildung.  
> **Stand:** April 2026 — alle bisherigen Phasen (Backend, Frontend, Multi-Provider) abgeschlossen.

---

## Uebersicht der 5 Module

| # | Modul | Prioritaet | Abhaengigkeiten | Geschaetzter Aufwand |
|---|---|---|---|---|
| 1 | Langzeitgedaechtnis | Hoechste | Keine | Mittel |
| 2 | Mehrdimensionale Meinung | Hoch | Keine | Mittel |
| 3 | Erweiterte Persona-Felder (Big Five + Demografie) | Hoch | Keine | Mittel |
| 4 | Chat-Gedaechtnis (DB-persistent) | Mittel | Modul 1 (nutzt selbe Memory-Infrastruktur) |  Mittel |
| 5 | Echokammer-Mechanik | Normal | Modul 2 (braucht numerische Meinungswerte) | Klein |

---

## Modul 1: Langzeitgedaechtnis

### Problem
Personas vergessen alles nach 5 Aktionen (Ringpuffer in `current_state.recent_actions`).  
Ein Mensch erinnert sich an praegende Erlebnisse ueber Wochen — besonders emotionale.

### Loesung

**Neues Feld `memory` (JSON-Array) im Persona-Modell:**

```json
{
  "memories": [
    {
      "tick": 3,
      "type": "conflict",
      "summary": "Heftiger Streit mit MaxMueller ueber den Preis — er nannte mich naiv",
      "emotional_weight": 0.9,
      "related_persona": "uuid-of-max",
      "related_post": "uuid-of-post"
    },
    {
      "tick": 7,
      "type": "persuasion",
      "summary": "Detaillierter Testbericht auf Threadit hat mich ueberzeugt — Akku haelt tatsaechlich 500km",
      "emotional_weight": 0.8,
      "related_post": "uuid-of-post"
    },
    {
      "tick": 12,
      "type": "social",
      "summary": "Meine beste Freundin Anna hat das Produkt bestellt — das beeinflusst mich",
      "emotional_weight": 0.6,
      "related_persona": "uuid-of-anna"
    }
  ]
}
```

**Memory-Typen:**
- `conflict` — Streit, Gegenargument, negative Erfahrung
- `persuasion` — Ueberzeugung durch Argumente oder Beweise
- `social` — Soziale Einfluesse (Freunde kaufen/lehnen ab)
- `surprise` — Unerwartete Information
- `personal` — Persoenliche Erfahrung mit dem Produkt/Thema

### Aenderungen

#### DB-Migration (009)
```sql
ALTER TABLE personas ADD COLUMN memory JSON DEFAULT '[]';
```

#### `app/models/persona.py`
- Neues Feld: `memory = Column(JSON, default=[])`

#### `app/simulation/tick_engine.py` — Memory-Extraction

**Neue Funktion `_extract_memory()`:**
Nach jedem State-Update wird geprueft ob die Aktion "erinnerungswuerdig" war.

Kriterien fuer Speicherung:
1. Persona hat ihre Meinung geaendert (opinion_evolution unterscheidet sich deutlich)
2. Ein Post hat die Persona besonders beeinflusst (`most_influential_post_id` ist gesetzt)
3. Persona war in einen Konflikt verwickelt (Dislike + Kommentar auf selben Post)
4. Persona hat zum ersten Mal gepostet oder zum ersten Mal reagiert

**Erweiterung des State-Update LLM-Calls:**
Das `state_update` Tool-Schema wird erweitert:

```json
{
  "opinion_evolution": "string",
  "mood": "string",
  "most_influential_post_id": "uuid or null",
  "memorable_event": {
    "should_remember": true/false,
    "type": "conflict|persuasion|social|surprise|personal",
    "summary": "1-2 Saetze was passiert ist und warum es wichtig war",
    "emotional_weight": 0.0-1.0
  }
}
```

**Memory-Management:**
- Max **30 Erinnerungen** pro Persona
- Wenn voll: niedrigstes `emotional_weight` wird entfernt
- Erinnerungen mit `emotional_weight < 0.3` verfallen nach 10 Ticks (Vergessen)
- Emotional gewichtete Erinnerungen (`>= 0.7`) verfallen nie

#### `app/simulation/tick_engine.py` — Memory im Prompt

**`_build_persona_profile_block()` erweitern:**
Die Top-5 relevantesten Erinnerungen (nach `emotional_weight` sortiert) werden dem Persona-Profil hinzugefuegt:

```
=== Deine praegenden Erinnerungen ===
[Tag 3] Heftiger Streit mit MaxMueller ueber den Preis (emotional: hoch)
[Tag 7] Testbericht auf Threadit hat mich ueberzeugt (emotional: hoch)
[Tag 12] Freundin Anna hat bestellt (emotional: mittel)
```

#### `app/routers/chat.py` — Memory im Chat
Alle Erinnerungen (nicht nur Top 5) werden in den Chat-System-Prompt geladen,  
damit die Persona im Gespraech auf vergangene Erlebnisse referenzieren kann.

---

## Modul 2: Mehrdimensionale Meinung

### Problem
`opinion_evolution` ist ein einziger Text der ueberschrieben wird.  
Keine numerische Verfolgung, keine Differenzierung nach Aspekten.

### Loesung

**Neues Feld `opinion_dimensions` (JSON) im `current_state`:**

```json
{
  "opinion_dimensions": {
    "product_quality":    0.6,
    "price_fairness":    -0.3,
    "brand_trust":        0.4,
    "innovation":         0.8,
    "ethical_concerns":   -0.1,
    "social_proof":       0.5,
    "personal_relevance": 0.3
  }
}
```

**Skala:** -1.0 (voellig negativ) bis +1.0 (voellig positiv)

**Dimensionen:**
| Dimension | Beschreibung |
|---|---|
| `product_quality` | Wahrgenommene Qualitaet des Produkts |
| `price_fairness` | Preis-Leistungs-Verhaeltnis |
| `brand_trust` | Vertrauen in die Marke |
| `innovation` | Wahrgenommener Innovationsgrad |
| `ethical_concerns` | Ethische/oekologische Bedenken (negativ = Bedenken) |
| `social_proof` | Wie stark Umfeld die Meinung beeinflusst |
| `personal_relevance` | Persoenliche Relevanz des Produkts |

### Aenderungen

#### `app/simulation/tick_engine.py` — State-Update Tool

**Erweitertes `state_update` Tool-Schema:**

```json
{
  "opinion_evolution": "string (weiterhin als Zusammenfassung)",
  "mood": "string",
  "most_influential_post_id": "uuid or null",
  "memorable_event": { ... },
  "opinion_shifts": {
    "product_quality":    0.0,
    "price_fairness":     0.0,
    "brand_trust":        0.0,
    "innovation":         0.0,
    "ethical_concerns":   0.0,
    "social_proof":       0.0,
    "personal_relevance": 0.0
  }
}
```

`opinion_shifts` sind **Deltas** (-0.3 bis +0.3 pro Tick).  
Werden auf die bestehenden `opinion_dimensions` addiert und auf [-1, 1] geclampt.

**Initialisierung:**  
Bei Persona-Generierung werden die Anfangswerte aus `initial_opinion` und `is_skeptic` abgeleitet:
- Skeptiker starten mit niedrigeren Werten (Durchschnitt ~-0.2)
- Nicht-Skeptiker starten neutral bis leicht positiv (Durchschnitt ~0.2)

#### `app/simulation/tick_engine.py` — Prompt-Anreicherung

Im Persona-Profil-Block werden die Dimensionen als lesbarer Text angezeigt:

```
=== Deine aktuelle Einstellung zum Produkt ===
Produktqualitaet: eher positiv (0.6)
Preis-Leistung: eher negativ (-0.3)
Markenvertrauen: leicht positiv (0.4)
Innovation: sehr positiv (0.8)
Ethische Bedenken: neutral (-0.1)
```

#### Frontend — Sentiment-Dashboard

Die bestehende Sentiment-Ansicht wird erweitert:
- **Radar-Chart** pro Persona (alle 7 Dimensionen)
- **Heatmap** ueber alle Personas (Dimension x Persona)
- **Zeitverlauf** pro Dimension (Line-Chart ueber Ticks)

#### Analyse-Report

Der Report-Generator erhaelt die Dimensionen aller Personas als Input.  
Ermoeglicht Aussagen wie: "73% der Skeptiker wurden bei Produktqualitaet ueberzeugt,  
aber der Preis bleibt fuer 61% ein Dealbreaker."

---

## Modul 3: Erweiterte Persona-Felder (Big Five + Demografie)

### Problem
Personas haben nur 10 Basis-Felder. Keine psychologische Tiefe,  
keine sozio-oekonomische Differenzierung.

### Loesung

**Neue Felder im Persona-Modell:**

#### Demografie (DB-Spalten)
| Feld | Typ | Beispiel |
|---|---|---|
| `education_level` | String(50) | "Hauptschule", "Ausbildung", "Bachelor", "Master", "Promotion" |
| `income_bracket` | String(30) | "niedrig", "mittel", "hoch", "sehr_hoch" |
| `family_status` | String(30) | "single", "partnerschaft", "familie_klein", "familie_gross", "alleinerziehend", "rentner" |
| `political_leaning` | String(30) | "links", "mitte-links", "mitte", "mitte-rechts", "rechts", "unpolitisch" |
| `media_consumption` | JSON | ["social_media", "qualitaetspresse", "boulevard", "podcasts", "tv"] |
| `tech_affinity` | Float | 0.0 (technikfern) bis 1.0 (early adopter) |

#### Big-Five-Persoenlichkeitsmodell (JSON in `personality_traits`)
```json
{
  "openness":          0.7,
  "conscientiousness": 0.4,
  "extraversion":      0.8,
  "agreeableness":     0.3,
  "neuroticism":       0.6
}
```

**Skala:** 0.0 (sehr niedrig) bis 1.0 (sehr hoch)

| Trait | Niedrig | Hoch | Simulations-Einfluss |
|---|---|---|---|
| Offenheit | Traditionell, risikoavers | Neugierig, experimentierfreudig | Beeinflusst Reaktion auf Innovation |
| Gewissenhaftigkeit | Impulsiv, spontan | Organisiert, gruendlich | Beeinflusst ob Persona recherchiert |
| Extraversion | Introvertiert, beobachtend | Gesellig, meinungsstark | Beeinflusst Post-Frequenz |
| Vertraeglichkeit | Konfrontativ, kritisch | Harmoniebeduertig, nachgiebig | Beeinflusst Dislike-Rate |
| Neurotizismus | Emotional stabil | Aengstlich, reaktiv | Beeinflusst Meinungswechsel-Geschwindigkeit |

### Aenderungen

#### DB-Migration (010)
```sql
ALTER TABLE personas ADD COLUMN education_level VARCHAR(50);
ALTER TABLE personas ADD COLUMN income_bracket VARCHAR(30);
ALTER TABLE personas ADD COLUMN family_status VARCHAR(30);
ALTER TABLE personas ADD COLUMN political_leaning VARCHAR(30);
ALTER TABLE personas ADD COLUMN media_consumption JSON DEFAULT '[]';
ALTER TABLE personas ADD COLUMN tech_affinity FLOAT DEFAULT 0.5;
ALTER TABLE personas ADD COLUMN personality_traits JSON DEFAULT '{}';
```

#### `app/simulation/persona_generator.py`

**Erweiterter Generation-Prompt:**

```
Erstelle {n} realistische Personas fuer den DACH-Raum.

WICHTIG fuer maximale Diversitaet:
- Alter: realistisch verteilt (18-80), nicht nur 25-45
- Bildung: von Hauptschule bis Promotion, realistisch verteilt
- Einkommen: proportional zu Bildung/Beruf, aber mit Ausnahmen
- Familienstatus: Singles, Paare, Familien, Alleinerziehende, Rentner
- Politisch: volle Bandbreite, nicht nur Mitte
- Technik-Affinitaet: vom Smartphone-Verweigerer bis zum Developer
- Big Five: realistische Verteilung, KEINE Durchschnittspersonen
  (extrem introvertierte Personen, sehr gewissenhafte, neurotische etc.)
- Min. 20% Skeptiker
- Min. 15% ueber 55 Jahre
- Min. 10% unter 25 Jahre
- Min. 10% ohne Hochschulabschluss
```

**Erweitertes Tool-Schema:**
Alle neuen Felder werden als required in das `create_personas` Tool-Schema aufgenommen.

#### `app/simulation/tick_engine.py` — Trait-basiertes Verhalten

**Big Five beeinflussen die Simulation:**

1. **Extraversion → Post-Wahrscheinlichkeit:**
   - Hohe Extraversion: Persona postet haeufiger, kommentiert mehr
   - Niedrige Extraversion: Persona beobachtet mehr, reagiert seltener

2. **Vertraeglichkeit → Reaktionstyp:**
   - Hohe Vertraeglichkeit: Mehr Likes, weniger Dislikes
   - Niedrige Vertraeglichkeit: Mehr Dislikes, schaerfere Kommentare

3. **Offenheit → Meinungsaenderung:**
   - Hohe Offenheit: `opinion_shifts` werden verstaerkt (x1.3)
   - Niedrige Offenheit: `opinion_shifts` werden gedaempft (x0.7)

4. **Neurotizismus → Emotionale Reaktivitaet:**
   - Hoher Neurotizismus: Staerkere Stimmungsschwankungen, hoehere `emotional_weight` bei Erinnerungen
   - Niedriger Neurotizismus: Stabilere Stimmung, langsame Meinungsaenderung

5. **Gewissenhaftigkeit → Informationsverarbeitung:**
   - Hohe Gewissenhaftigkeit: Persona bezieht sich auf Fakten, bevorzugt Threadit
   - Niedrige Gewissenhaftigkeit: Persona reagiert emotional, bevorzugt FeedBook

**Implementierung:** Diese Modifikatoren werden als Multiplikatoren im Prompt und bei der  
Verarbeitung der LLM-Antworten angewendet (nicht als harte Regeln, sondern als Tendenz).

---

## Modul 4: Chat-Gedaechtnis (DB-persistent)

### Problem
Chat-Verlaeufe leben nur im Frontend. Beim Neuladen ist alles weg.  
Persona erinnert sich nicht an vorherige Gespraeche mit dem User.

### Loesung

#### Neue DB-Tabelle `persona_conversations`

```sql
CREATE TABLE persona_conversations (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    persona_id    UUID NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
    messages      JSON NOT NULL DEFAULT '[]',
    summary       TEXT,
    message_count INT NOT NULL DEFAULT 0,
    created_at    TIMESTAMP NOT NULL DEFAULT now(),
    updated_at    TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX idx_persona_conversations_persona ON persona_conversations(persona_id);
```

#### Conversation-Flow

1. **Neues Gespraech starten:** `POST /personas/{id}/chat/start` → erstellt `persona_conversations`-Eintrag, gibt `conversation_id` zurueck
2. **Nachricht senden:** `POST /personas/{id}/chat` mit `conversation_id` → laedt bisherigen Verlauf aus DB, haengt neue Nachricht an, speichert zurueck
3. **Gespraeche auflisten:** `GET /personas/{id}/conversations` → Liste aller Gespraeche mit Vorschau
4. **Gespraech laden:** `GET /personas/{id}/conversations/{conv_id}` → vollstaendiger Verlauf

#### Zusammenfassung nach Gespraech

Wenn ein Gespraech **>= 6 Nachrichten** hat und der User 2 Minuten nicht antwortet  
(oder explizit beendet), wird automatisch eine Zusammenfassung generiert:

```python
summary = await provider.chat(
    tier="fast",
    system="Fasse dieses Gespraech in 2-3 Saetzen zusammen. Was war das Thema? Wie war die Stimmung?",
    messages=conversation_messages,
    max_tokens=200,
)
```

Diese Zusammenfassung wird:
1. In `persona_conversations.summary` gespeichert
2. Als `memory`-Eintrag (Typ `personal`, emotional_weight 0.5) in die Persona geschrieben
3. In zukuenftige Chat-System-Prompts geladen:

```
=== Fruehere Gespraeche ===
[Gespraech 1] User hat nach Preis gefragt. Ich war skeptisch, User hat gute Argumente gebracht.
[Gespraech 2] User wollte wissen warum ich meine Meinung geaendert habe. Entspanntes Gespraech.
```

#### Frontend-Aenderungen

- **Chat-Panel:** Conversation-Selector (Tabs oder Dropdown) fuer mehrere Gespraeche
- **Gespraechs-Historie:** Liste vergangener Gespraeche mit Zusammenfassung
- **Auto-Persist:** Jede Nachricht wird sofort in der DB gespeichert (kein Datenverlust)

---

## Modul 5: Echokammer-Mechanik

### Problem
Der Feed-Algorithmus bevorzugt nur Engagement (Likes, Kommentare) und soziale Naehe.  
Keine Verstaerkung bestehender Ueberzeugungen.

### Loesung

#### Feed-Algorithmus erweitern (`build_feed()`)

**Neuer Scoring-Faktor: Confirmation Bias**

```python
def _confirmation_bias_score(persona, post, all_personas) -> float:
    """Berechnet wie sehr ein Post die bestehende Meinung bestaetigt."""
    persona_dims = persona.current_state.get("opinion_dimensions", {})
    if not persona_dims:
        return 0.0

    # Durschnittliche Meinung der Persona
    avg_opinion = sum(persona_dims.values()) / len(persona_dims)

    # Schaetzen ob der Post-Autor aehnlich denkt
    author = next((p for p in all_personas if p.id == post.author_id), None)
    if not author:
        return 0.0
    author_dims = (author.current_state or {}).get("opinion_dimensions", {})
    if not author_dims:
        return 0.0
    author_avg = sum(author_dims.values()) / len(author_dims)

    # Aehnliche Meinung = hoehere Relevanz
    similarity = 1.0 - abs(avg_opinion - author_avg)
    return similarity * 2.0  # Bis zu +2.0 Scoring-Bonus
```

**Integration in `build_feed()` (Zeile ~140):**

```python
# Bestehende Scores
score += confirmation_bias_score  # Neuer Faktor

# Negativ-Korrektur: Personas mit hoher Offenheit (Big Five)
# bekommen WENIGER Echokammer-Effekt
openness = (persona.personality_traits or {}).get("openness", 0.5)
if openness > 0.7:
    score *= 0.7  # Offene Personas sehen diverseren Content
```

#### Polarisierungs-Tracking

Neues Feld in `SimulationTick.snapshot`:

```json
{
  "polarization_index": 0.0-1.0,
  "echo_chamber_clusters": [
    {"personas": ["id1", "id2"], "avg_opinion": 0.7},
    {"personas": ["id3", "id4"], "avg_opinion": -0.5}
  ]
}
```

Der `polarization_index` wird pro Tick berechnet als Standardabweichung  
der durchschnittlichen `opinion_dimensions` aller Personas.  
Hoher Wert = Gesellschaft ist gespalten.

#### Frontend

- **Neues Widget im Dashboard:** "Polarisierungs-Index" als Gauge-Chart
- **Cluster-Visualisierung:** Im Netzwerk-Tab Faerbung nach Meinungscluster

---

## Implementierungs-Reihenfolge

```
Modul 1: Langzeitgedaechtnis
  ├── DB-Migration (memory-Feld)
  ├── State-Update Tool-Schema erweitern
  ├── Memory-Extraction Logik
  ├── Memory im Persona-Profil-Block
  └── Memory im Chat-Prompt
       ↓
Modul 2: Mehrdimensionale Meinung
  ├── opinion_dimensions in current_state
  ├── State-Update Tool-Schema erweitern (opinion_shifts)
  ├── Initialisierung bei Persona-Generierung
  ├── Prompt-Anreicherung
  └── Frontend Radar-Chart + Heatmap
       ↓
Modul 3: Erweiterte Persona-Felder
  ├── DB-Migration (7 neue Spalten)
  ├── Generation-Prompt erweitern
  ├── Tool-Schema erweitern
  ├── Big-Five-Modifikatoren in Tick-Engine
  └── Frontend Persona-Detail-Ansicht
       ↓
Modul 4: Chat-Gedaechtnis
  ├── DB-Tabelle persona_conversations
  ├── Chat-Endpoints erweitern (start/persist/list)
  ├── Auto-Zusammenfassung
  ├── Zusammenfassung → Memory-Integration
  └── Frontend Conversation-Selector
       ↓
Modul 5: Echokammern
  ├── Confirmation-Bias im Feed-Scoring
  ├── Big-Five-Korrektur (Offenheit)
  ├── Polarisierungs-Index Berechnung
  └── Frontend Gauge + Cluster-Visualisierung
```

---

## Betroffene Dateien (Uebersicht)

| Datei | Module |
|---|---|
| `app/models/persona.py` | 1, 3 |
| `app/simulation/persona_generator.py` | 2, 3 |
| `app/simulation/tick_engine.py` | 1, 2, 3, 5 |
| `app/routers/chat.py` | 1, 4 |
| `app/analysis/report_generator.py` | 2 |
| `alembic/versions/009_*.py` | 1 |
| `alembic/versions/010_*.py` | 3, 4 |
| `frontend/.../personas/` | 2, 3 |
| `frontend/.../sentiment/` | 2 |
| `frontend/.../network/` | 5 |
| `frontend/.../tools/` (Chat) | 4 |

---

## Risiken & Mitigationen

| Risiko | Mitigation |
|---|---|
| Memory-Feld wird zu gross (>100KB pro Persona) | Max 30 Erinnerungen, Vergessens-Mechanik |
| Big-Five-Multiplikatoren machen Simulation deterministisch | Multiplikatoren als Tendenz (±30%), nicht als harte Regeln |
| Mehrdimensionale Meinung ueberfordert Fast-Modell (Haiku) | Shifts als einfache Zahlen, kein komplexes Reasoning noetig |
| Echokammer verstaerkt sich zu schnell | Confirmation-Bias-Score gedeckelt auf +2.0, Offenheits-Korrektur |
| Chat-Zusammenfassung kostet extra API-Calls | Nur bei >= 6 Nachrichten, Fast-Tier (guenstig) |
| Token-Kosten steigen durch laengere Prompts | Memory: nur Top-5 im Tick-Prompt, alle im Chat-Prompt |
