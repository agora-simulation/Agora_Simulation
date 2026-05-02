# Implementierungsplan: Marktforschungs-Analyse-Tool

> Basierend auf Tiefenrecherche zu Marktforschungsmethodik, Datenstrukturen, Analysemethoden, KPIs, Simulation, Reporting, Compliance und aktuellen Trends (2025/2026).

---

## Priorisierungsmatrix

| Prioritaet | Kriterium |
|------------|-----------|
| **P0 - Kritisch** | Grundlegende Analysefaehigkeit, ohne die das Tool keinen Marktforschungswert hat |
| **P1 - Hoch** | Differenzierungsmerkmale, die das Tool von Wettbewerbern abheben |
| **P2 - Mittel** | Erweiterte Features fuer professionelle Nutzer |
| **P3 - Niedrig** | Nice-to-have, langfristige Vision |

---

## Phase 1: Analytik-Fundament (P0)

### 1.1 KPI-Engine

**Ziel**: Automatische Berechnung von Marktforschungs-Standard-KPIs aus Simulationsdaten.

**Zu implementierende KPIs:**

| KPI | Berechnung aus Simulationsdaten | Anzeige |
|-----|--------------------------------|---------|
| **Simulated NPS** | Aus Opinion-Dimensionen (quality + trust + relevance) auf 0-10 Skala mappen → Promoter/Detractor/Passive | Gauge + Trend |
| **Brand Awareness** | Anteil Personas, die mind. 1x ueber das Produkt gepostet/kommentiert haben | Prozent + Trend |
| **Share of Voice** | Anteil produktbezogener Posts an Gesamtposts pro Tick | Linie ueber Zeit |
| **Engagement Rate** | (Reactions + Comments) / Posts pro Tick | Linie ueber Zeit |
| **Adoption Rate** | Anteil Personas mit positivem Opinion-Shift (>0.5) ueber Zeit | S-Kurve |
| **Virality Coefficient** | Durchschnittliche Anzahl Sekundaer-Interaktionen pro Original-Post | Zahl + Trend |
| **Sentiment Score** | Gewichteter Durchschnitt aller Opinion-Dimensionen pro Tick | Linie ueber Zeit |
| **Churn Risk** | Personas mit negativem Opinion-Trend ueber 3+ Ticks | Prozent + Liste |

**Technische Umsetzung:**
- Neuer Service: `app/analysis/kpi_engine.py`
- Berechnung nach Simulation-Completion + optional live pro Tick
- REST-Endpunkt: `GET /api/simulations/{id}/kpis`
- Frontend: KPI-Dashboard-Tab oder Integration in Overview

---

### 1.2 Netzwerk-Metriken

**Ziel**: Berechnung und Anzeige wissenschaftlich fundierter Netzwerk-Zentralitaetsmetriken.

**Metriken:**

| Metrik | Bedeutung | Nutzen |
|--------|-----------|--------|
| **Degree Centrality** | Anzahl direkter Verbindungen | Wer ist am vernetztesten? |
| **Betweenness Centrality** | Brueckenfunktion zwischen Clustern | Wer verbindet Gruppen? (Gatekeeper) |
| **Eigenvector Centrality** | Qualitaet der Verbindungen | Wer kennt die Einflussreichen? |
| **Closeness Centrality** | Durchschnittliche Distanz zu allen | Wer erreicht alle am schnellsten? |
| **Clustering Coefficient** | Vernetztheit der Nachbarn untereinander | Wo sind Echo Chambers? |

**Technische Umsetzung:**
- Library: `networkx` (Python) fuer serverseitige Berechnung
- Neuer Service: `app/analysis/network_metrics.py`
- REST-Endpunkt: `GET /api/simulations/{id}/network-metrics`
- Frontend: Integration in Netzwerk-Tab mit Persona-Ranking nach jeder Metrik
- Visuelle Kodierung: Knotengroesse = Centrality, Farbe = Community/Cluster

---

### 1.3 Erweiterte Influence-Analyse

**Ziel**: Nachvollziehbare Influence-Ketten statt nur aggregierter Zahlen (adressiert bestehende Issues).

**Features:**
- **Influence-Trail**: Fuer jedes Influence-Event: Wer → Wen → Durch welchen Post → Welcher Opinion-Shift
- **Kaskaden-Visualisierung**: Baumstruktur zeigt, wie sich ein Post durch das Netzwerk verbreitet
- **Top-Influencer-Detail**: Aufschluesselung pro Persona: beeinflusste Personas, Posts, Staerke
- **Influence-Timeline**: Alle Events aller Tage filterbar (nicht nur Tag 1)
- **Influence-Heatmap**: Matrix Persona x Persona, Farbintensitaet = Einflussstaerke

**Technische Umsetzung:**
- Backend: Erweiterte Queries auf InfluenceEvent mit Joins zu Posts/Personas
- REST: `GET /api/simulations/{id}/influence-chains?persona_id=X`
- Frontend: Interaktiver Drill-Down in Influence-Tab

---

## Phase 2: Simulations-Erweiterungen (P1)

### 2.1 Szenario-Vergleich (A/B-Simulation)

**Ziel**: Zwei Simulationen mit unterschiedlichen Parametern vergleichen (z.B. mit vs. ohne Influencer-Kampagne).

**Features:**
- Simulation klonen mit geaenderten Parametern
- Side-by-Side-Dashboard: KPIs, Sentiment-Verlauf, Adoption-Kurve im Direktvergleich
- Delta-Analyse: Wo weichen die Ergebnisse signifikant ab?
- Export: Vergleichsreport als PDF/Markdown

**Datenmodell-Erweiterung:**
```
SimulationComparison:
  - id
  - name
  - simulation_a_id (FK)
  - simulation_b_id (FK)
  - comparison_config (JSON: welche Metriken vergleichen)
  - created_at
```

**Technische Umsetzung:**
- Backend: `app/analysis/comparison_engine.py`
- REST: `POST /api/comparisons`, `GET /api/comparisons/{id}/results`
- Frontend: Neuer Vergleichs-View mit synchronisierten Charts

---

### 2.2 Externe Events / Schoecke

**Ziel**: Simulation von externen Einfluessen waehrend des Laufs (PR-Krise, Wettbewerber-Launch, virale Kampagne).

**Event-Typen:**

| Event | Auswirkung | Parameter |
|-------|-----------|-----------|
| **PR-Krise** | Negativer Sentiment-Schock, Trust sinkt | Staerke, betroffene Segmente |
| **Wettbewerber-Launch** | Aufmerksamkeit sinkt, Vergleichsdiskussionen | Produktaehnlichkeit |
| **Influencer-Kampagne** | Gezielte Opinion-Shifts bei Followern | Influencer-Profil, Reichweite |
| **Medienberichterstattung** | Breiter Awareness-Boost oder -Drop | Tonalitaet, Reichweite |
| **Regulierung/Gesetz** | Veraenderte Rahmenbedingungen | Betroffene Branchen |
| **Viraler Moment** | Exponentielles Engagement | Ausgangs-Post, Viralitaet |

**Datenmodell-Erweiterung:**
```
SimulationEvent:
  - id
  - simulation_id (FK)
  - tick_number (wann tritt das Event ein)
  - event_type (enum)
  - severity (0.0-1.0)
  - description (Text fuer LLM-Context)
  - affected_segments (JSON: demografisch/psychografisch)
  - created_at
```

**Technische Umsetzung:**
- Events werden vor Simulationsstart oder waehrend der Laufzeit definiert
- Tick-Engine injiziert Event-Kontext in den LLM-Prompt des betroffenen Ticks
- Personas reagieren natuerlich auf Events basierend auf ihrer Persoenlichkeit
- Frontend: Event-Timeline mit Markern im Sentiment-Verlauf

---

### 2.3 Multi-Run / Monte-Carlo-Modus

**Ziel**: Gleiche Konfiguration N-mal laufen lassen → statistische Konfidenz statt Einzelergebnis.

**Features:**
- Konfiguration: Anzahl Runs (z.B. 5-20)
- Aggregierte Ergebnisse: Mittelwert, Standardabweichung, Konfidenzintervalle fuer alle KPIs
- Robustheits-Score: Wie konsistent sind die Ergebnisse ueber alle Runs?
- Worst-Case / Best-Case Identifikation

**Technische Umsetzung:**
- Neues Modell: `SimulationBatch` mit 1:N Beziehung zu Simulations
- Backend: Batch-Runner der sequentiell oder parallel (bei ausreichend API-Budget) laeuft
- REST: `POST /api/simulation-batches`, `GET /api/simulation-batches/{id}/aggregate`
- Frontend: Ergebnisse als Bandbreiten-Charts (Konfidenzbaender)

---

## Phase 3: Segmentierung und Datenstruktur (P1)

### 3.1 Automatische Persona-Segmentierung

**Ziel**: Personas werden nicht nur generiert, sondern automatisch in Marktsegmente gruppiert.

**Methoden:**
- **K-Means Clustering** auf Basis von: Opinion-Dimensionen, Big-Five-Traits, Verhaltensdaten
- **Segmentnamen** per LLM generiert (z.B. "Technik-Enthusiasten", "Preis-Skeptiker", "Loyale Frueh-Adopter")
- **Segment-Evolution**: Wie veraendern sich Segmente ueber die Ticks?

**Technische Umsetzung:**
- Library: `scikit-learn` fuer Clustering
- Service: `app/analysis/segmentation.py`
- Personas erhalten `segment_id` nach Clustering
- Frontend: Segment-Filter in allen Views, Segment-Vergleichs-Dashboard

---

### 3.2 Erweiterte Persona-Typen (aus Issues)

**Ziel**: Nicht nur Individuen, sondern auch Organisationen, Institutionen, Politiker als eigenstaendige Akteure.

**Persona-Typen und ihre Besonderheiten:**

| Typ | Verhalten | Einfluss |
|-----|-----------|----------|
| **Individuum** | Persoenliche Meinung, emotional | Peer-to-Peer |
| **Unternehmen** | Strategisch, markenkonform | Hohe Reichweite, Werbung |
| **Bildungseinrichtung** | Faktenbasiert, paedagogisch | Expertise, Vertrauen |
| **Verein/NGO** | Wertegetrieben, aktivistisch | Community-Mobilisierung |
| **Politiker** | Agenda-getrieben, oeffentlich | Policy, breite Aufmerksamkeit |
| **Pruefstelle/Forschung** | Objektiv, evidenzbasiert | Hohe Glaubwuerdigkeit |
| **Medien** | Berichterstattung, Reichweite | Agenda-Setting |

**Technische Umsetzung:**
- `persona_type` Enum erweitern (teilweise schon vorhanden: individual, organization, institution, politician)
- Typ-spezifische LLM-Prompts fuer Verhaltensgenerierung
- Typ-spezifische Netzwerk-Rollen (z.B. Medien als Hub-Nodes)
- Intelligente Zuordnung: LLM entscheidet basierend auf Produkt/Branche, welche Typen relevant sind

---

### 3.3 Gewichtungs- und Repraesentativitaets-System

**Ziel**: Sicherstellen, dass die Persona-Verteilung reale Marktverhaeltnisse widerspiegelt.

**Features:**
- Konfigurierbare Gewichtung: Alter, Einkommen, Region, Persona-Typ
- Vergleich mit realen Zensusdaten (optional)
- Gewichtungsreport im Analyse-Output
- Bias-Indikator: Wie repraesentativ ist die Stichprobe?

---

## Phase 4: Reporting-Erweiterungen (P2)

### 4.1 Strukturierter Analyse-Report

**Ziel**: Report folgt wissenschaftlicher Marktforschungs-Struktur statt freiem Text.

**Report-Sektionen (Standard):**

1. **Executive Summary** — Kernbefunde in 3-5 Saetzen
2. **Methodik** — Simulationsparameter, Persona-Verteilung, Laufzeit
3. **Marktueberblick** — Simuliertes Marktumfeld, Segmentverteilung
4. **Adoption & Diffusion** — S-Kurve, Bass-Modell-Vergleich, Adoptionsrate
5. **Sentiment-Analyse** — Verlauf, Wendepunkte, Treiber
6. **Segmentanalyse** — Pro Segment: KPIs, Verhalten, Empfaenglichkeit
7. **Netzwerk & Einfluss** — Top-Influencer, Echo Chambers, Kaskaden
8. **Risiken & Kritik** — Identifizierte Negativtrends, Angriffspunkte
9. **Chancen & Empfehlungen** — Handlungsempfehlungen pro Segment
10. **Szenario-Vergleich** (falls vorhanden) — Delta-Analyse
11. **Methodische Einschraenkungen** — LLM-Bias-Disclaimer, Stichprobengroesse

**Technische Umsetzung:**
- Modularer Report-Generator: jede Sektion als eigene Funktion
- Jede Sektion erhaelt relevante Daten als Input (nicht alles auf einmal)
- Export: Markdown, PDF, PowerPoint (langfristig)

---

### 4.2 Erweiterte Visualisierungen

**Neue Charts fuer das Dashboard:**

| Chart | Tab | Datenquelle |
|-------|-----|-------------|
| **Radar-Chart** | Personas | Big-Five + Opinion-Dimensionen pro Persona/Segment |
| **Sankey-Diagramm** | Influence | Influence-Flow zwischen Segmenten/Persona-Typen |
| **Heatmap** | Sentiment | Meinungskorrelation zwischen Opinion-Dimensionen |
| **S-Kurve (Bass)** | Overview | Adoption-Rate mit theoretischer Bass-Kurve als Overlay |
| **Bubble-Chart** | Network | x=Betweenness, y=Eigenvector, Size=Posts, Color=Sentiment |
| **Stacked Area** | Sentiment | Anteil positiv/neutral/negativ ueber Zeit |
| **Box-Plots** | KPIs | Verteilung von KPIs ueber Monte-Carlo-Runs |

**Libraries:**
- Frontend: `ngx-echarts` oder `d3.js` (fuer Sankey, Netzwerk)
- Bestehende Charts erweitern, nicht ersetzen

---

### 4.3 Interaktive Filter und Drill-Down

**Ziel**: Nutzer kann jede Analyse nach Segmenten, Persona-Typ, Zeitraum und Plattform filtern.

**Globale Filter:**
- Zeitraum (Tick-Range)
- Persona-Typ (Individuum, Organisation, ...)
- Segment (automatisch oder manuell)
- Plattform (FeedBook, Threadit)
- Stimmung (positiv, neutral, negativ)

---

## Phase 5: Validierung und Compliance (P2)

### 5.1 Bias-Transparenz

**Ziel**: Nutzer verstehen die Grenzen der Simulation.

**Features:**
- **LLM-Bias-Disclaimer** im Report: Erklaerung, dass LLMs inherente Biases haben
- **Diversity-Score**: Wie divers ist die Persona-Stichprobe? (Alter, Geschlecht, Einkommen, Meinung)
- **Skeptiker-Anteil-Indikator**: Anzeige des tatsaechlichen Skeptiker-Anteils
- **Konsistenz-Check**: Verhalten Personas sich konsistent zu ihrem Profil?

---

### 5.2 Validierungsmodus (langfristig)

**Ziel**: Vergleich von Simulationsergebnissen mit realen Marktdaten.

**Features:**
- Import von realen Umfragedaten (CSV/JSON)
- Automatischer Vergleich: Simulierte vs. reale KPIs
- Abweichungs-Report mit Erklaerungsansaetzen
- Kalibrierungsvorschlaege fuer zukuenftige Simulationen

---

## Phase 6: Zukunftsfeatures (P3)

### 6.1 Predictive Analytics
- Trend-Extrapolation ueber Simulationsende hinaus
- "Was waere wenn"-Szenarien basierend auf aktuellen Daten
- Automatische Empfehlungen fuer optimale Marketingstrategien

### 6.2 Conjoint-Analyse-Modus
- Personas bewerten Produktkonfigurationen (Features, Preise)
- Berechnung von Teilnutzenwerten
- Optimale Produktkonfiguration ableiten

### 6.3 Real-Time Research Integration
- Live-Daten aus echten Social-Media-Quellen einspeisen
- Hybridmodell: Echte Daten + simulierte Ergaenzung
- Continuous Tracking statt einmaliger Simulation

### 6.4 Export und Integration
- PDF-Report-Export mit professionellem Layout
- PowerPoint-Export fuer Praesentationen
- API fuer Integration in bestehende Marktforschungs-Plattformen
- Webhook-Erweiterungen fuer Automatisierung

---

## Technische Abhaengigkeiten

```
Phase 1 (Analytik-Fundament)
  ├── 1.1 KPI-Engine ← keine Abhaengigkeit
  ├── 1.2 Netzwerk-Metriken ← networkx installieren
  └── 1.3 Erweiterte Influence-Analyse ← bestehende InfluenceEvent-Daten

Phase 2 (Simulations-Erweiterungen)
  ├── 2.1 Szenario-Vergleich ← benoetigt 1.1 (KPIs zum Vergleichen)
  ├── 2.2 Externe Events ← Tick-Engine Erweiterung
  └── 2.3 Monte-Carlo ← benoetigt 2.1 (fuer Aggregation)

Phase 3 (Segmentierung)
  ├── 3.1 Auto-Segmentierung ← scikit-learn, benoetigt 1.1
  ├── 3.2 Erweiterte Persona-Typen ← Persona-Generator Erweiterung
  └── 3.3 Gewichtungssystem ← benoetigt 3.1

Phase 4 (Reporting)
  ├── 4.1 Strukturierter Report ← benoetigt 1.1, 1.2, 3.1
  ├── 4.2 Visualisierungen ← Frontend, unabhaengig
  └── 4.3 Filter/Drill-Down ← Frontend, unabhaengig

Phase 5 (Validierung)
  ├── 5.1 Bias-Transparenz ← benoetigt 3.1, 3.3
  └── 5.2 Validierungsmodus ← benoetigt 1.1

Phase 6 (Zukunft)
  └── Alle ← benoetigen Phase 1-4
```

---

## Empfohlene Reihenfolge

| Schritt | Feature | Aufwand | Impact |
|---------|---------|---------|--------|
| 1 | KPI-Engine (1.1) | Mittel | Sehr hoch — Basis fuer alles |
| 2 | Netzwerk-Metriken (1.2) | Niedrig | Hoch — schneller Mehrwert |
| 3 | Erweiterte Influence-Analyse (1.3) | Mittel | Hoch — loest bekannte Issues |
| 4 | Erweiterte Visualisierungen (4.2) | Mittel | Hoch — sofort sichtbar |
| 5 | Interaktive Filter (4.3) | Mittel | Hoch — Usability |
| 6 | Externe Events (2.2) | Mittel | Hoch — Differenzierung |
| 7 | Auto-Segmentierung (3.1) | Mittel | Hoch — Marktforschungs-Kern |
| 8 | Erweiterte Persona-Typen (3.2) | Hoch | Hoch — aus Issues |
| 9 | Strukturierter Report (4.1) | Mittel | Mittel — Professionalitaet |
| 10 | Szenario-Vergleich (2.1) | Hoch | Mittel — Differenzierung |
| 11 | Bias-Transparenz (5.1) | Niedrig | Mittel — Vertrauen |
| 12 | Monte-Carlo (2.3) | Hoch | Mittel — wissenschaftliche Validitaet |
| 13 | Gewichtungssystem (3.3) | Mittel | Mittel — Repraesentativitaet |
| 14+ | Phase 6 Features | Sehr hoch | Langfristig |

---

## Quellen der Recherche

- Cogitaris: Marktforschung 2025
- Acxiom: Psychographic vs Demographic vs Behavioral Segmentation
- Resonio: Data Analysis Methods in Market Research
- TandFOnline: Agent-Based Modeling for Economic Markets (2026)
- ArXiv: LLM Multi-Agent Systems
- Wikipedia: Bass Diffusion Model
- JASSS: Hegselmann-Krause Bounded Confidence Model
- Qualtrics: AI Market Research Report 2025
- Stratega Research: Market Research Trends 2026
- Rival Group: 2026 Market Research Trends Report
- ESOMAR/ICC: Internationaler Kodex fuer Markt- und Sozialforschung
- Dr. Datenschutz: DSGVO bei Marktforschung
- SmartyAds/Gartner: Brand Awareness KPIs
- Emerald: Marketing and Social Networks (SNA)
