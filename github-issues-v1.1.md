# GitHub Issues v1.1 – Agora System-Erweiterung

> **Update v1.1:** Anpassungen nach Realtest-Auswertung (15-Tage-Sim, ChargeBot M50). Neue/geänderte Issues sind mit **(v1.1)** markiert.
>
> **Wichtig:** Bevor mit der Umsetzung begonnen wird, muss zuerst **EPIC #0 (Konzept & Architektur)** abgeschlossen sein.
>
> **Hinweis zu Tests:** Aufgrund von API-Kosten wird "Dry Build, Wet Validate" angewandt – siehe Architektur-Dokument v1.1, Abschnitt 15.

---

## Epic-Übersicht (v1.1)

| # | Epic | Phase | Aufwand | Abhängigkeit | Priorität |
|---|------|-------|---------|--------------|-----------|
| 0 | Konzept & Architektur | 0 | M | — | KRITISCH (zuerst) |
| 1 | Akteurs-System (Herzstück) | 1 | XL | #0 | KRITISCH |
| 2 | Crowd-Layer | 2 | L | #1 | HOCH |
| 3 | Recherche-Modul | 3 | L | #0 | HOCH |
| 4 | Verteilungs-System & UI | 4 | M | #1 | MITTEL |
| 5 | Influence-Network-Erweiterung | 5 | M | #1 | MITTEL |
| 6 | Reporting-Erweiterung | 6 | M | #1, #2 | MITTEL |
| 7 | Template-System | 7 | M | #3, #4 | MITTEL |
| 8 | Polish, Onboarding & Validierung | 8 | M | alle | NIEDRIG |
| **9** | **Plattform-Layer (NEU v1.1)** | **1** | **M** | **#1** | **HOCH** |

---

# EPIC #0: Konzept & Architektur

**Labels:** `epic`, `concept`, `blocker`
**Phase:** 0
**Aufwand:** M (1–2 Wochen)
**Abhängigkeiten:** —

## Ziel
Vollständige konzeptionelle Klärung aller Design-Entscheidungen.

## Sub-Issues
- [ ] #0.1 Akteurs-Schema final dokumentieren (alle 9 Typen + Crowd + Plattformen)
- [ ] #0.2 Profil-Felder pro Akteurs-Typ definieren (inkl. context, traegerschaft)
- [ ] #0.3 Verhaltens-Parameter pro Typ
- [ ] #0.4 Stance-Konzept finalisieren
- [ ] #0.5 Beziehungs-Layer-Konzept
- [ ] #0.6 Datenmodell-Migration planen (Schema-Änderung + neue Tabellen)
- [ ] #0.7 UI-Architektur-Konzept (5 Sidebar-Reiter, Quick-Start vs. Power)
- [ ] #0.8 Erfolgskriterien definieren
- [ ] #0.9 Mock-Modus-Konzept
- [ ] #0.10 Architektur-Dokument finalisieren und als `doku/architektur.md` einchecken
- [ ] **#0.11 Funktions-Tag-System konzipieren (NEU v1.1)**
- [ ] **#0.12 Trigger-Event-Schema konzipieren (NEU v1.1)**
- [ ] **#0.13 Stagnations-Detection-Algorithmus konzipieren (NEU v1.1)**
- [ ] **#0.14 Plattform-Layer-Schema konzipieren (NEU v1.1)**
- [ ] **#0.15 Validierer-Verhalten konzipieren (binäre Signale, langsame Reaktion) (NEU v1.1)**

## Akzeptanzkriterien
- [ ] Architektur-Dokument v1.1 liegt im Repo und ist reviewed
- [ ] Datenmodell-Migration ist als Alembic-Migration vorbereitet
- [ ] Alle 9 Akteurs-Typen + Plattform-Layer haben dokumentierte Schemata
- [ ] Mock-Modus ist als Konzept beschrieben

---

# EPIC #1: Akteurs-System (Herzstück)

**Labels:** `epic`, `core`, `feature`
**Phase:** 1
**Aufwand:** XL (4–5 Wochen, leicht erweitert in v1.1)
**Abhängigkeiten:** #0

## Ziel
Erweiterung des Persona-Systems von "200 Personas in 3 Kategorien" auf ein differenziertes 9-Typen-System mit Funktions-Tags, Dimensionen und Trigger-Mechanik.

## Priorität innerhalb des Epics (v1.1)
1. **Trigger-System + Stagnations-Detection** (löst Realtest-Hauptproblem!)
2. **Validierer-Typ** (war im Realtest deutliche Lücke)
3. **Context-Dimension** auf Privatperson (B2B-Tauglichkeit)
4. **Trägerschaft-Dimension** (öffentliche Akteure)
5. Alle anderen Typen-Schemata
6. Tonalitäts-Templates
7. Beziehungs-Layer (kann V2)

## Sub-Issues

### Datenmodell

- [ ] **#1.1** DB-Schema-Erweiterung: `personas`-Tabelle um `actor_type`, `subtype`, `stance`, `activation_latency`, `trigger_condition`, `profile_data` erweitern
- [ ] **#1.2** Neue Tabelle: `actor_relationships` für Beziehungen zwischen Personas
- [ ] **#1.3** Pydantic-Modelle pro Akteurs-Typ (Discriminated Union)
- [ ] **#1.4** Profil-Felder als JSON-Spalte mit Pydantic-Validierung
- [ ] **#1.4a** **(NEU v1.1)** Felder hinzufügen: `context`, `traegerschaft`, `function_tags`, `engagement_decay_rate`

### Akteurs-Typen implementieren

- [ ] **#1.5** Privatperson – Big Five + demografisch + **`context`-Dimension (privat/beruflich/öffentlich) (v1.1)**
- [ ] **#1.6** Firma – inkl. **`traegerschaft`-Dimension und `rechtsform` (v1.1)**
- [ ] **#1.7** Institut/Forschung – inkl. `traegerschaft`
- [ ] **#1.8** Behörde – inkl. erweiterte Stance-Optionen (v1.1)
- [ ] **#1.9** Medium – inkl. `traegerschaft`
- [ ] **#1.10** Influencer – inkl. **`context` (consumer/business/politisch) (v1.1)**
- [ ] **#1.11** Experte – inkl. **`affiliation_type` (v1.1)**
- [ ] **#1.12** Kollektiver Akteur (Subtypen) – inkl. `function_tags`
- [ ] **#1.13** **~~Gatekeeper~~ → ENTFÄLLT (v1.1: Gatekeeper wird Funktions-Tag)**
- [ ] **#1.13a** **(NEU v1.1) Validierer/Zertifizierer-Typ implementieren** (TÜV, VdS, BNetzA, Versicherer, Eichämter)
- [ ] **#1.13b** **(NEU v1.1) Validierer-Verhalten:** binäre Signale (`freigabe_status`), Anfrage-getrieben statt Tick-getrieben

### Funktions-Tag-System (NEU v1.1)

- [ ] **#1.14** **(NEU v1.1)** Tag-Schema definieren: `meinungs_gatekeeper`, `marktzugangs_gatekeeper`, `bruckenakteur`, `multiplikator`, `polarisierer`, `early_signal_giver`
- [ ] **#1.14a** **(NEU v1.1)** Tag-Modifikatoren in Influence-Network-Berechnung integrieren
- [ ] **#1.14b** **(NEU v1.1)** Auto-Detection von Tags aus Sim-Verlauf (Brückenakteur erkennen, Multiplikator erkennen)
- [ ] **#1.14c** **(NEU v1.1)** Tag-Vergabe manuell in UI (Power-Modus)

### Generierungs-Logik

- [ ] **#1.15** Generierungs-Prompts pro Akteurs-Typ (mind. ein Default pro Typ)
- [ ] **#1.16** Hybrid-Generation pro Typ erweitern
- [ ] **#1.17** Persona-Diversität sicherstellen (Persönlichkeits-Modulation)

### Verhaltens-Logik (Tick-Loop)

- [ ] **#1.18** Tick-Loop um Akteurs-Typ-Auswertung erweitern
- [ ] **#1.19** Posting-Frequenz pro Typ
- [ ] **#1.20** Aktivierungs-Latenz **(PFLICHT v1.1, war optional)**
- [ ] **#1.21** Trigger-Bedingungen **(PFLICHT v1.1)**
- [ ] **#1.21a** **(NEU v1.1)** `engagement_decay_rate` implementieren (Akteure kühlen wieder ab)
- [ ] **#1.22** Dropout/Lurking-Mechanik (75/9/1-Regel)
- [ ] **#1.23** Persona-Lifecycle: Eintritt und Austritt

### Trigger-System (NEU v1.1, KRITISCH)

- [ ] **#1.24** **(NEU v1.1)** Datenmodell: `trigger_events`-Tabelle (id, simulation_id, tick_day, event_type, title, content, affected_segments, intensity)
- [ ] **#1.24a** **(NEU v1.1)** Event-Types: `news_headline`, `competitor_action`, `regulatory_change`, `validator_decision`, `social_incident`
- [ ] **#1.24b** **(NEU v1.1)** Tick-Loop um Trigger-Auswertung erweitern (welche Akteure reagieren auf welches Event?)
- [ ] **#1.24c** **(NEU v1.1)** Trigger-Effekt auf Crowd-Layer (Volumen-Spike, Sentiment-Shift)
- [ ] **#1.24d** **(NEU v1.1)** UI: Trigger-Editor (Zeitachse mit Drag-and-Drop von Events)
- [ ] **#1.24e** **(NEU v1.1)** UI: Live-Trigger während laufender Sim einwerfen
- [ ] **#1.24f** **(NEU v1.1)** Im Report: ausgewiesen "Trigger-Event an Tag X verschob Sentiment um Y"

### Stagnations-Detection (NEU v1.1, KRITISCH)

- [ ] **#1.25** **(NEU v1.1)** Detection-Algorithmus: Posts/Tick + Sentiment-Varianz + neue Argumente
- [ ] **#1.25a** **(NEU v1.1)** Auto-Reactivation: latente Akteure mit höchstem Reichweiten-Potenzial aktivieren
- [ ] **#1.25b** **(NEU v1.1)** Auto-Reactivation: zufälliges News-Event aus konfigurierter Library generieren
- [ ] **#1.25c** **(NEU v1.1)** Konfigurations-Profile: "Aus", "Mild", "Aggressiv"
- [ ] **#1.25d** **(NEU v1.1)** Im Report: Stagnations-Events ausweisen

### Verhaltens-Prompts

- [ ] **#1.26** Verhaltens-Prompts pro Typ
- [ ] **#1.27** Tonalitäts-Basis pro Typ (Vorbereitung für EPIC #7)

### UI: Persona-Cards

- [ ] **#1.28** Persona-Card-Component generisch refactorn
- [ ] **#1.29** Typ-spezifische Card-Inhalte
- [ ] **#1.30** Typ-spezifischer Radar-Chart
- [ ] **#1.31** Persona-Liste mit Filter nach Akteurs-Typ
- [ ] **#1.32** Chat-mit-Persona für alle Typen aktivieren
- [ ] **#1.32a** **(NEU v1.1)** Validierer-Card zeigt `freigabe_status` prominent

## Akzeptanzkriterien
- [ ] DB-Migration läuft sauber durch (auf leerer DB getestet)
- [ ] Alle 9 Typen können generiert werden (Mini-Sim: 1 Persona pro Typ)
- [ ] Generierung funktioniert mit Mock-Modus ohne API-Calls
- [ ] Tick-Loop respektiert Latenz und Trigger
- [ ] **(v1.1) Trigger-Events haben messbare Wirkung im Tick-Loop**
- [ ] **(v1.1) Stagnations-Detection feuert in Test-Szenario "leere Sim"**
- [ ] **(v1.1) Validierer-Posts haben Hauptsignal-Charakter (werden zitiert)**

---

# EPIC #2: Crowd-Layer (Resonanzraum)

**Labels:** `epic`, `feature`, `simulation`
**Phase:** 2
**Aufwand:** L (2 Wochen)
**Abhängigkeiten:** #1, #9 (Plattform-Layer)

## Ziel
Aufbau einer parallelen Schicht zur Persona-Ebene, die das anonyme Hintergrundrauschen modelliert.

## Sub-Issues

- [ ] **#2.1** Datenmodell: `crowd_state`-Tabelle (pro Plattform/Tick)
- [ ] **#2.2** Crowd-Reaktion auf Akteurs-Posts
- [ ] **#2.3** Crowd-Wirkung auf Personas (Bandwagon-Effekt)
- [ ] **#2.4** Crowd-Eigendynamik (Selbstverstärkung)
- [ ] **#2.5** Crowd-Reaktion modellieren (anonyme Schwarmstimmen)
- [ ] **#2.6** Crowd-Mood Visualisierung im Dashboard
- [ ] **#2.7** Crowd-Aggregat im Influence-Flow sichtbar machen
- [ ] **#2.8** "Chat mit Crowd" – aggregierte Stimme zur Befragung
- [ ] **#2.9** **(NEU v1.1)** Crowd reagiert auf Trigger-Events (Volumen-Spike bei News-Injection)
- [ ] **#2.10** **(NEU v1.1)** Crowd pro Plattform getrennt (siehe EPIC #9)

## Akzeptanzkriterien
- [ ] Crowd-Layer läuft parallel zum Tick-Loop ohne Performance-Verschlechterung
- [ ] Bandwagon-Effekt ist im Report nachvollziehbar
- [ ] Visualisierung intuitiv (User versteht Crowd-Dynamik in <30 Sekunden)
- [ ] **(v1.1) Trigger-Events erzeugen sichtbaren Crowd-Spike**

---

# EPIC #3: Recherche-Modul (Phase-1-Outsourcing)

**Labels:** `epic`, `feature`, `module`
**Phase:** 3
**Aufwand:** L (2 Wochen)
**Abhängigkeiten:** #0

## Ziel
Auslagerung der Marktrecherche aus dem Simulations-Workflow.

## Sub-Issues

### Modul-Grundgerüst

- [ ] **#3.1** Neuer Sidebar-Reiter "Recherche"
- [ ] **#3.2** Datenmodell: `research_snapshots`-Tabelle
- [ ] **#3.3** CRUD-Endpoints (`/research/`)
- [ ] **#3.4** UI: Recherche-Liste, -Detail, -Erstellen, -Bearbeiten, -Löschen

### Recherche-Erstellung

- [ ] **#3.5** LLM-Auswahl pro Recherche
- [ ] **#3.6** Eigener Prompt-Editor
- [ ] **#3.7** Multi-Pass-Pipeline (5 Pässe)
- [ ] **#3.8** Live-Vorschau während Recherche-Lauf (SSE)
- [ ] **#3.9** Recherche-Output strukturiert speichern

### Recherche-Templates

- [ ] **#3.10** Default-Templates: B2C-Konsum, B2B-Software, **B2B-Industriegut (NEU v1.1)**, Forschungskampagne, Politische Initiative, Healthcare/Pharma, Finanz
- [ ] **#3.11** Template auswählen → Prompts vorbelegt

### Integration in Simulation

- [ ] **#3.12** Bestehender "Deep Mode" entkoppeln und entfernen
- [ ] **#3.13** Bei Sim-Erstellung: Auswahl "Recherche zuweisen"
- [ ] **#3.14** Alternative: "Inline-Recherche" für Schnellnutzer
- [ ] **#3.15** Recherche-Output in Persona-Generierung einspeisen
- [ ] **#3.16** Recherche-Output in Tick-Loop verfügbar

### Trigger-Library aus Recherche (NEU v1.1)

- [ ] **#3.17** **(NEU v1.1)** Recherche generiert Liste von **vorgeschlagenen Trigger-Events** (z.B. "Wettbewerber X plant Launch in Q3", "Behörde Y prüft neue Verordnung")
- [ ] **#3.18** **(NEU v1.1)** User kann diese Events direkt in Sim-Trigger-Library übernehmen

### Multi-Run-Konsistenz

- [ ] **#3.19** Multi-Run nutzt automatisch dieselbe Recherche

## Akzeptanzkriterien
- [ ] Recherche eigenständig erstellbar und speicherbar
- [ ] Wiederverwendung in mehreren Sims funktioniert
- [ ] Multi-Run reproduzierbar
- [ ] **(v1.1) Trigger-Vorschläge erscheinen in der Recherche**

---

# EPIC #4: Verteilungs-System & Konfigurator-UI

**Labels:** `epic`, `feature`, `ui`
**Phase:** 4
**Aufwand:** M (1–2 Wochen)
**Abhängigkeiten:** #1

## Ziel
UI für die Steuerung der Akteurs-Verteilung in einer Simulation.

## Sub-Issues

- [ ] **#4.1** Verteilungs-Editor: Slider pro Akteurs-Typ (0–100%)
- [ ] **#4.2** Live-Validierung: Summe = 100%
- [ ] **#4.3** Auto-Balance-Button
- [ ] **#4.4** Akteurs-Typ deaktivieren
- [ ] **#4.5** Verteilungs-Templates: B2C-Konsum, B2B-Software, **B2B-Industriegut (NEU v1.1)**, Forschungskampagne, Politische Initiative, Healthcare/Pharma, Finanz, Custom
- [ ] **#4.6** Verteilungs-Vorschau ("Bei 200 Personas wären das: ...")
- [ ] **#4.7** Optional/V2: Zeitkurve
- [ ] **#4.8** Subtyp-Verteilung (z.B. innerhalb Kollektive Akteure)
- [ ] **#4.9** Stance-Verteilung pro Typ
- [ ] **#4.10** **(NEU v1.1)** Context-Verteilung bei Privatperson (privat/beruflich/öffentlich)
- [ ] **#4.11** **(NEU v1.1)** Trägerschaft-Verteilung bei Organisations-Typen
- [ ] **#4.12** **(NEU v1.1)** Mindest-Bucket-Warnung (3 Personas pro aktivem Typ minimum)

## Akzeptanzkriterien
- [ ] User kann in <2 Minuten custom Verteilung anlegen
- [ ] Templates funktionieren als Quick-Start
- [ ] Generierung respektiert Verteilung exakt (±1 Persona Toleranz)
- [ ] **(v1.1) Warnung bei <3 Personas in einem aktiven Typ**

---

# EPIC #5: Influence-Network-Erweiterung

**Labels:** `epic`, `feature`, `simulation`
**Phase:** 5
**Aufwand:** M (1–2 Wochen)
**Abhängigkeiten:** #1, #9

## Ziel
Influence-Netzwerk erweitern, sodass Edges typ- und plattform-gewichtet sind.

## Sub-Issues

- [ ] **#5.1** Edge-Gewichtung nach Akteurs-Typ-Kombination
- [ ] **#5.2** Reichweiten-Multiplikator je Typ
- [ ] **#5.3** Glaubwürdigkeits-Score je Typ
- [ ] **#5.4** Themen-Spezifität (Behörde/Validierer nur in Domäne wirksam)
- [ ] **#5.5** Beziehungs-Layer als optionales Vorab-Setup
- [ ] **#5.6** Beziehungen aus Recherche ableitbar
- [ ] **#5.7** Influence-Flow-Visualisierung
- [ ] **#5.8** **(NEU v1.1)** Plattform-Multiplikator in Edge-Berechnung
- [ ] **#5.9** **(NEU v1.1)** Function-Tag-Modifier in Edge-Berechnung
- [ ] **#5.10** **(NEU v1.1)** Validierer-Edge: bei `freigabe_status`-Änderung viral

## Akzeptanzkriterien
- [ ] Behörden-Post hat messbar mehr Wirkung als Privatperson-Post
- [ ] Influence-Flow zeigt User die wichtigsten Akteure
- [ ] **(v1.1) Plattform-Wirkung ist im Network sichtbar (Threadit ≠ Feedbook)**

---

# EPIC #6: Reporting-Erweiterung

**Labels:** `epic`, `feature`, `analytics`
**Phase:** 6
**Aufwand:** M (1–2 Wochen, +1 Woche in v1.1)
**Abhängigkeiten:** #1, #2, #9

## Ziel
Analyse-Report differenziert Ergebnisse nach Akteurs-Typ und macht alle Dynamiken transparent.

## Sub-Issues

- [ ] **#6.1** Report-Sektion "Sentiment nach Akteurs-Typ" **(PFLICHT v1.1, war optional)**
- [ ] **#6.2** Report-Sektion "Influence Flow" mit Multiplikator-Effekten
- [ ] **#6.3** Report-Sektion "Crowd-Verlauf"
- [ ] **#6.4** Typ-spezifische Confidence-Ratings
- [ ] **#6.5** Stance-Aufschlüsselung
- [ ] **#6.6** Wendepunkt-Detection mit Kausalzuordnung
- [ ] **#6.7** Beziehungs-Effekte
- [ ] **#6.8** Vergleichs-Report für Multi-Run
- [ ] **#6.9** **(NEU v1.1)** Plattform-Vergleich-Sektion (Threadit vs. Feedbook etc.)
- [ ] **#6.10** **(NEU v1.1)** Validierer-Status-Sektion ("TÜV: pending", "VdS: approved")
- [ ] **#6.11** **(NEU v1.1)** Trigger-Event-Wirkung-Sektion ("News an Tag 5 verschob Sentiment")
- [ ] **#6.12** **(NEU v1.1)** Quoten-Format mit Konfidenzintervall (siehe Architektur 11.2)
- [ ] **#6.13** **(NEU v1.1)** Stagnations-Events ausweisen
- [ ] **#6.14** **(NEU v1.1)** Function-Tag-Übersicht ("Top-3 Brückenakteure", "Top-5 Multiplikatoren")
- [ ] **#6.15** Methodische Grenzen-Sektion bleibt 1:1 (sehr gut)

## Akzeptanzkriterien
- [ ] Report ist auch für Marktforschungs-Laien verständlich
- [ ] Confidence-Ratings je Sektion sichtbar
- [ ] Multi-Run-Vergleich zeigt klar Stabilität und Effektgröße
- [ ] **(v1.1) Sentiment nach Typ ist Pflicht-Sektion**
- [ ] **(v1.1) Quoten-Aussagen haben einheitliches Format mit KI**

---

# EPIC #7: Template-System (übergreifend)

**Labels:** `epic`, `feature`, `system`
**Phase:** 7
**Aufwand:** M (1–2 Wochen)
**Abhängigkeiten:** #3, #4

## Ziel
Einheitliches Template-System für alle vier Kategorien.

## Sub-Issues

### System-Grundlage

- [ ] **#7.1** Datenmodell: `templates`-Tabelle
- [ ] **#7.2** CRUD-Endpoints (`/templates/`)
- [ ] **#7.3** Generisches Template-UI

### Vier Template-Kategorien (v1.1)

- [ ] **#7.4** Kategorie "Recherche-Templates"
- [ ] **#7.5** Kategorie "Verteilungs-Templates"
- [ ] **#7.6** Kategorie "Tonalitäts-Templates" pro Akteurs-Typ
- [ ] **#7.6a** **(NEU v1.1)** Kategorie "Trigger-Library" (vorgefertigte News-Events pro Branche)

### Tonalitäts-Templates im Detail

- [ ] **#7.7** Default-Tonalitäten pro Typ definieren
- [ ] **#7.8** Pro Typ duplizierbar
- [ ] **#7.9** Tonalitäts-Auswahl bei Sim-Erstellung
- [ ] **#7.9a** **(NEU v1.1)** Validierer-Tonalität definieren (formal-technisch)

### Trigger-Library im Detail (NEU v1.1)

- [ ] **#7.10** **(NEU v1.1)** Default-Trigger-Library pro Branche (mind. 6 Events pro Branche)
- [ ] **#7.11** **(NEU v1.1)** UI: Trigger-Library-Editor (anlegen, duplizieren, anpassen)
- [ ] **#7.12** **(NEU v1.1)** Trigger-Library mit Verteilungs-Template kombinierbar (Branchen-Paket)

### Branchen-Pakete

- [ ] **#7.13** Konzept "Branchen-Paket" = Recherche + Verteilung + Tonalität + **Trigger-Library (v1.1)**
- [ ] **#7.14** Default-Pakete: Heizungsbau-DE, B2B-SaaS, Pharma, Politik, **E-Mobility-DACH (NEU v1.1)**
- [ ] **#7.15** UI: "Paket auswählen" als One-Click-Konfiguration

### Export/Import (V2)

- [ ] **#7.16** Template-Export als JSON
- [ ] **#7.17** Template-Import

### Versionierung (V2)

- [ ] **#7.18** Templates versionieren

## Akzeptanzkriterien
- [ ] Vier Template-Kategorien funktionieren mit gleicher Pattern
- [ ] User kann Branchen-Paket in <30 Sekunden auswählen
- [ ] Templates pro User-Account isoliert
- [ ] **(v1.1) Trigger-Library ist als 4. Kategorie verfügbar**

---

# EPIC #8: Polish, Onboarding & Validierung

**Labels:** `epic`, `polish`, `onboarding`
**Phase:** 8 (zum Schluss)
**Aufwand:** M (1–2 Wochen)
**Abhängigkeiten:** alle

## Ziel
System rund machen, Einstiegshürde senken, Vertrauen durch Validierung.

## Sub-Issues

### Onboarding

- [ ] **#8.1** Quick-Start-Modus: 3 Eingaben, alles auf Defaults
- [ ] **#8.2** Power-Modus: Vollkonfiguration
- [ ] **#8.3** Tooltip-Guide beim ersten Login
- [ ] **#8.4** Beispiel-Sim als Demo

### UI-Architektur final

- [ ] **#8.5** Sidebar-Reorganisation: Simulationen, Neue Simulation, Recherche, Templates, Einstellungen
- [ ] **#8.6** Konsistentes Design-System
- [ ] **#8.7** Mobile/Tablet-Anpassung (optional)

### Validierung

- [ ] **#8.8** Backtest-Konzept: dokumentierte Markteinführung modellieren
- [ ] **#8.9** Mind. 3 Backtests durchführen und im Repo dokumentieren
- [ ] **#8.10** "Validierungs-Statement" im README ergänzen
- [ ] **#8.10a** **(NEU v1.1)** **Zweite Realtest-Sim als Pflicht-Validierung** (5–10 Tage, mit Trigger-Events, prüft ob Stagnation behoben)

### Performance & Kostenoptimierung

- [ ] **#8.11** Caching für identische LLM-Anfragen
- [ ] **#8.12** Modell-Tier-Auto-Switch
- [ ] **#8.13** Token-Verbrauchs-Anzeige pro Sim

### Dokumentation

- [ ] **#8.14** README aktualisieren
- [ ] **#8.15** Doku-Ordner erweitern (`doku/akteure/`, `doku/recherche/`, `doku/templates/`, `doku/trigger/`)
- [ ] **#8.16** Beispiel-Workflows als Markdown
- [ ] **#8.17** **(NEU v1.1)** Doku zu Validierer-Typ und Trigger-System (eigene Sektion)

## Akzeptanzkriterien
- [ ] Neuer User kann in <5 Minuten erste Sim starten
- [ ] Mind. 1 Backtest zeigt qualitative Übereinstimmung mit realem Markt
- [ ] Token-Anzeige stimmt mit echter Rechnung (±10%)
- [ ] **(v1.1) Zweite Realtest-Sim zeigt keine Stagnation mehr (Hauptkriterium!)**

---

# EPIC #9 (NEU v1.1): Plattform-Layer

**Labels:** `epic`, `feature`, `simulation`
**Phase:** 1 (parallel zu EPIC #1)
**Aufwand:** M (1–2 Wochen)
**Abhängigkeiten:** #0

## Ziel
Formalisierung der bisher impliziten Plattform-Differenzierung (Threadit/Feedbook) zu einer vollwertigen architektonischen Schicht.

## Sub-Issues

### Datenmodell

- [ ] **#9.1** Datenmodell: `platforms`-Tabelle (id, name, character, tonality_modifier, reach_multiplier, preferred_actor_types, echo_chamber_strength, default_engagement_rate)
- [ ] **#9.2** Default-Plattformen migrieren: Threadit (operativ), Feedbook (institutionell)
- [ ] **#9.3** Akteurs-Plattform-Affinitäts-Matrix als Konfiguration

### Erweiterte Plattformen

- [ ] **#9.4** Optionale weitere Default-Plattformen: Newsfeed (boulevard), Fachforum (fachlich), Öffentliche Petition (öffentlich)

### Logik-Integration

- [ ] **#9.5** Tick-Loop: pro Plattform getrennte Verarbeitung
- [ ] **#9.6** Cross-Posting: Akteure können auf mehreren Plattformen aktiv sein (typ-abhängig)
- [ ] **#9.7** Plattform-Tonalitäts-Modifier in Verhaltens-Prompts einbauen
- [ ] **#9.8** Plattform-Reach-Multiplier in Influence-Network einbauen

### UI

- [ ] **#9.9** Plattform-Editor in Einstellungen (aktivieren/deaktivieren, Custom anlegen)
- [ ] **#9.10** Plattform-Affinitäten anpassbar pro Sim
- [ ] **#9.11** Im Report: Plattform-Vergleich-Sektion

### Crowd-Integration

- [ ] **#9.12** Crowd-Layer pro Plattform getrennt (siehe EPIC #2)

## Akzeptanzkriterien
- [ ] Plattformen sind als eigene DB-Entität persistent
- [ ] Threadit und Feedbook funktionieren als Default-Plattformen
- [ ] User kann Custom-Plattform anlegen
- [ ] Cross-Posting funktioniert für Influencer und Medien automatisch
- [ ] Im Report ist klar erkennbar, welche Plattform welche Dynamik hatte

---

# Globale Hinweise (v1.1)

## Entwicklungs-Pattern: "Dry Build, Wet Validate"

Aufgrund von API-Kostenrestriktionen wird wie folgt entwickelt:

1. **Schema, Datenmodell, Migrations** → keine API
2. **UI gegen Mock-Daten** → keine API
3. **Prompts in Markdown ausarbeiten** → keine API
4. **Tick-Loop-Algorithmik** → keine API
5. **Trigger-System (v1.1)** → komplett deterministisch testbar, keine API
6. **Stagnations-Detection (v1.1)** → reine Mathematik, keine API
7. **Punktuelle Integration** → einzelne API-Calls mit Fast-Tier
8. **Voll-Sim-Tests** → nur an Meilensteinen, mit Mini-Sample (5–10 Personas, 3–5 Ticks, Fast-Tier)

## Mock-Modus (Issue #0.9)

Zentrales Werkzeug:
- Alle LLM-Calls werden durch deterministische Fixtures ersetzt
- UI vollständig durchklickbar ohne API-Verbrauch
- Tick-Loop läuft mit pre-canned Posts/Reactions
- Aktivierbar per Env-Variable `MOCK_MODE=true`

## Geplanter Realtest nach Implementierung (5–10 Tage)

Bei der Pflicht-Validierungs-Sim (Issue #8.10a) sollten gezielt geprüft werden:

- [ ] Sentiment nach Akteurs-Typ wird korrekt im Report ausgewiesen
- [ ] Validierer (TÜV/VdS) tauchen als eigene Akteure auf
- [ ] Privatperson-Context (beruflich) wird bei FM-Leads gesetzt
- [ ] Mindestens ein Trigger-Event wird eingespeist und Wirkung ist messbar
- [ ] Stagnations-Detection feuert (oder beweist, dass keine Stagnation)
- [ ] Plattform-Vergleich Threadit/Feedbook ist explizit im Report
- [ ] Quoten-Aussagen haben standardisiertes Format mit KI

## Labels

- `epic` – Sammel-Issue für ein ganzes Feature-Paket
- `core` – Herzstück, kritischer Pfad
- `feature` – neue Funktionalität
- `refactor` – Umbau bestehender Logik
- `infra` – Infrastruktur, DB, Deployment
- `ui` – Frontend-Arbeit
- `concept` – Designarbeit ohne Code
- `blocker` – blockiert andere Issues
- `polish` – Verfeinerung
- `onboarding` – Einstiegs-Erleichterung
- `analytics` – Reporting, Auswertung
- `simulation` – Tick-Loop, Engine
- `module` – größerer Block, eigenes Modul
- `system` – übergreifend
- `v1.1` – aus v1.1-Update (Realtest-Erkenntnisse)

## Statistik der v1.1-Erweiterungen

| Metrik | v1.0 | v1.1 |
|--------|------|------|
| Anzahl Epics | 9 | 10 (+1 Plattform-Layer) |
| Anzahl Sub-Issues | ~100 | ~135 (+35 neu) |
| Geschätzte Gesamtzeit | 3–5 Monate | 4–6 Monate |
| Hauptänderungen | — | Validierer-Typ, Trigger-System, Stagnations-Detection, Plattform-Layer, Funktions-Tags, Trägerschaft, Context-Dimension |

