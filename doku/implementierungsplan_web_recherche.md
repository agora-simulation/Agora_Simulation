# Implementierungsplan: Web-Recherche-Integration

## Ziel
Vor der Persona-Generierung eine automatische Web-Recherche durchführen, die den aktuellen
Makro-, Branchen- und Zielgruppen-Kontext erfasst. Personas und Simulation werden dadurch
an die Realität von HEUTE geerdet, nicht an statisches LLM-Trainingswissen.

## Modi
- **Quick Mode** (default): Keine Recherche, sofort Personas generieren (wie bisher)
- **Deep Mode**: Web-Recherche → Market Context Document → Personas + Simulation nutzen Kontext

---

## Phase 1: Data Model + SimulationStatus

### 1.1 SimulationStatus erweitern
- Neuer Status `researching` zwischen `pending` und `running`
- Flow: `pending` → `researching` → `running` → `completed`

### 1.2 MarketContext Model
- Eigene Tabelle `market_contexts`
- Felder: macro_context, industry_context, target_group_context, raw_sources, research_mode
- Wiederverwendbar: Mehrere Simulationen können den gleichen Context nutzen
- FK: simulation_id (optional — Context kann auch standalone existieren)

### 1.3 SimulationCreate erweitern
- Neues Feld `research_mode: "quick" | "deep"` (default: "quick")

---

## Phase 2: Research Engine

### 2.1 Web-Search-Wrapper
- `app/research/web_search.py`
- DuckDuckGo Search (kostenlos, kein API-Key nötig)
- Fallback auf LLM-Wissen wenn Search fehlschlägt
- Rate-Limiting: max 10 Queries pro Recherche

### 2.2 Context Builder
- `app/research/context_builder.py`
- LLM generiert Suchqueries basierend auf Produkt/Markt/Branche
- Sucht Web-Ergebnisse, fasst sie zusammen
- Output: Strukturiertes MarketContext-JSON mit 3 Schichten:
  1. Makro-Kontext (Wirtschaft, Politik, Gesellschaft)
  2. Branchen-Kontext (News, Wettbewerb, Regulierung)
  3. Zielgruppen-Kontext (Trends, Schmerzpunkte, Stimmung)

### 2.3 Research Orchestrator
- `app/research/research_agent.py`
- Koordiniert Search + LLM-Calls
- Speichert MarketContext in DB
- Error Handling: Bei Fehler → Fallback auf LLM-Wissen (kein Abbruch)

---

## Phase 3: Integration

### 3.1 Persona-Generator
- `_build_prompt()` bekommt optionalen MarketContext-Parameter
- Context wird als "Aktuelle Marktlage"-Sektion in den Prompt eingefügt
- Personas werden im Kontext der aktuellen Realität generiert

### 3.2 Tick-Engine
- `AGENT_SYSTEM_PROMPT` bekommt optionalen Markt-Kontext
- Personas reagieren im Kontext aktueller Ereignisse
- Context wird einmalig geladen und für alle Ticks cached

### 3.3 Runner
- `run_simulation_background()` prüft research_mode
- Bei "deep": Erst Recherche, dann Personas, dann Ticks
- Status-Updates: pending → researching → running → completed

---

## Phase 4: API + Schemas

### 4.1 Endpoints
- `GET /simulations/{id}/market-context` — Context-Document anzeigen
- `PUT /simulations/{id}/market-context` — Context manuell editieren
- `POST /simulations/{id}/research` — Recherche manuell neu starten

### 4.2 Schema-Updates
- SimulationCreate: + research_mode
- SimulationRead: + research_mode, market_context_id
- MarketContextRead: Vollständiges Context-Document

---

## Status

- [x] Phase 1 — Data Model + Status
- [x] Phase 2 — Research Engine
- [x] Phase 3 — Integration
- [x] Phase 4 — API + Schemas
