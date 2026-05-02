# Implementierungsplan: Simulation Akkuratesse & Belastbarkeit

## Ziel
Die Sim-Engine von einer Spielerei zu einem ernsthaften Pre-Screening-Tool für Marktforschung entwickeln. Firmen sollen damit evaluieren können, ob eine vollumfängliche Marktanalyse sinnvoll ist.

---

## Phase 1: Sofort-Maßnahmen (Belastbarkeit)

### 1.1 Multi-Run mit Varianz-Analyse
- Neues Feld `run_group_id` in Simulation-Model
- Endpoint `/simulations/{id}/multi-run` für N Parallelläufe (default: 3)
- Jeder Run: andere Persona-Konstellationen, andere Wave-Reihenfolgen
- Vergleichs-Report: Konvergenz-Konsistenz, Sentiment-Bandbreite, Narrativ-Stabilität
- **Output: Konfidenz-Score pro Erkenntnis** ("4/5 Runs: Compliance-Narrativ dominant")

### 1.2 Quantitative Claims unterbinden
- AGENT_SYSTEM_PROMPT erweitern: Personas dürfen keine konkreten Zahlen/Prozente erfinden
- Nur qualitative Aussagen erlaubt ("deutlich bessere Ergebnisse" statt "+23% CTR")
- Report-Generator: Flagging von quantitativen Claims als "Persona-Behauptung, nicht validiert"

### 1.3 Confirmation-Bias reduzieren
- Feed-Scoring: Confirmation-Bias-Bonus von +2.0 auf +0.5 senken
- Opposing-View-Injection: Min. 1 Post aus gegenteiligem Meinungslager pro Feed
- Konsens-Bremse: Bei Polarization-Index < 0.15 kontroverse Stimmen im Ranking bevorzugen

---

## Phase 2: Meinungsdynamik (Realismus)

### 2.1 Conviction Strength & Bounded Confidence
- Neues Feld `conviction` (0.0-1.0) pro Persona + Dimension
- Max Opinion-Shift: `0.3 * (1.0 - conviction * 0.7)`
- Bounded Confidence (Deffuant-Weisbuch): Shift nur wenn `|eigene_meinung - post_meinung| < threshold`
- Conviction steigt bei Bestätigung, sinkt bei überzeugender Gegenargumentation

### 2.2 Opposing-View-Garantie im Feed
- Jeder Feed enthält mindestens 1-2 Posts aus dem gegenteiligen Meinungslager
- Gewichtung: Qualität/Reaktionen des Gegen-Posts bestimmen Platzierung
- Verhindert Filter-Bubbles innerhalb der Simulation

### 2.3 Memory-System verbessern
- Top-5 → Top-10 Memories für Agent-Actions
- Periodische Memory-Kompression: "Zusammenfassung der letzten 5 Tage"
- Core Memories: Besonders meinungsändernde Momente permanent halten

---

## Phase 3: Validierung (Vertrauen)

### 3.1 Stress-Tests
- Contrarian-Injection: Tag 7+14 automatisch starke Gegen-Narrative
- Sensitivity-Test: Gleicher Run mit 60% statt default Skeptikern
- Remove-and-Rerun: Einflussreichsten Akteur entfernen, Stabilität prüfen

### 3.2 Report mit Konfidenz-Levels
- `high_confidence`: >80% Run-Konsistenz + stress-resistent
- `medium_confidence`: 50-80% konsistent
- `low_confidence`: <50%, möglicherweise Artefakt
- Expliziter Abschnitt: "Was diese Simulation NICHT leisten kann"
- Vergleichs-Tabelle über alle Runs

---

## Phase 4: Kalibrierung (Premium)

### 4.1 Persona-Kalibrierung gegen echte Daten
- DACH-Demographie-Profile (Statistisches Bundesamt)
- Rogers Diffusion of Innovation Verteilung (2.5/13.5/34/34/16%)
- Branchenspezifische Adoption-Kurven
- Optional: Nutzer-eigene Zielgruppen-Daten hochladen

---

## Umsetzungs-Reihenfolge

| Phase | Maßnahme | Aufwand | Impact |
|-------|----------|---------|--------|
| **1** | Multi-Run + Varianz | Mittel | Sehr hoch |
| **1** | Quantitative Claims unterbinden | Klein | Hoch |
| **1** | Confirmation-Bias reduzieren | Klein | Hoch |
| **2** | Conviction + Bounded Confidence | Mittel | Sehr hoch |
| **2** | Opposing-View-Injection | Klein | Hoch |
| **2** | Memory verbessern | Klein | Mittel |
| **3** | Stress-Tests | Mittel | Hoch |
| **3** | Report Konfidenz-Levels | Mittel | Hoch |
| **4** | Persona-Kalibrierung | Groß | Mittel |

---

## Status

- [x] Phase 1.1 — Multi-Run
- [x] Phase 1.2 — Quantitative Claims
- [x] Phase 1.3 — Confirmation-Bias
- [x] Phase 2.1 — Conviction & Bounded Confidence
- [x] Phase 2.2 — Opposing-View-Feed (in 1.3 integriert)
- [x] Phase 2.3 — Memory
- [x] Phase 3.1 — Stress-Tests
- [x] Phase 3.2 — Report Konfidenz
- [x] Phase 4.1 — Persona-Kalibrierung
