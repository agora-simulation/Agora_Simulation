# Agora – Architektur-Dokument: System-Erweiterung

**Status:** v1.1 (Update nach Realtest)
**Letzte Änderung:** 04.05.2026
**Vorgängerversion:** v1.0 (gleichtägig)
**Zweck:** Konzeptionelle Grundlage für die Erweiterung von Agora_Simulation um Akteurs-Typen, Crowd-Layer, eigenständige Recherche, Plattform-Layer und Template-System.

> **Vorgehen:** Dieses Dokument muss vor Beginn der Umsetzung von dir reviewed und freigegeben werden. Es dient als Single Source of Truth, gegen die alle GitHub-Issues abgearbeitet werden.

---

## Changelog v1.1

Auswertung einer realen 15-Tage-Simulation (200 Personas, B2B DACH, ChargeBot M50) ergab folgende notwendige Anpassungen:

| # | Änderung | Begründung aus Realtest |
|---|----------|-------------------------|
| 1 | **Akteurs-Typ #9 Gatekeeper → Validierer/Zertifizierer** | Gatekeeper-Funktion ist nicht typgebunden (Verbände UND Handel können Gatekeeper sein). Validierer (TÜV, VdS, BNetzA, Versicherer) tauchten in der Sim als kritische, separate Akteurs-Klasse auf. |
| 2 | **Funktions-Tag-System eingeführt** (statt Gatekeeper als Typ) | "Meinungs-Gatekeeper", "Marktzugangs-Gatekeeper", "Brückenakteur" sind Rollen, die verschiedene Typen einnehmen können. |
| 3 | **Neue Dimension `traegerschaft`** auf Organisations-Typen | Sim zeigte viele AöR (Anstalt öffentlichen Rechts) – weder reine Firma noch reine Behörde. Privat/öffentlich/genossenschaftlich/gemischt/kommunal. |
| 4 | **Neue Dimension `context`** auf Privatperson | B2B-Sims haben viele "individuelle" Akteure (FM-Leads, Einkäufer), die NICHT private Konsumenten sind. Privat / beruflich / öffentlich. |
| 5 | **Plattform-Layer als architektonisches Element** (vorher: Persona-Eigenschaft) | Das aktuelle System hat bereits Threadit/Feedbook implizit – das soll als formale Schicht mit Tonalität, Reichweiten-Charakter und Akteurs-Affinität ausgebaut werden. |
| 6 | **Latenz und Trigger sind PFLICHT, nicht optional** | Sim verlor Momentum ab Tag 10 ("Musterfortschreibung") – ohne Trigger-Events stagniert jede Sim. |
| 7 | **News-Injection als First-Class-Feature** | User muss an beliebigen Tagen Events einspeisen können (Wettbewerber-Launch, Behörden-Bescheid, Skandal). |
| 8 | **Stagnations-Detection mit Auto-Reactivation** | System erkennt selbst, wenn Sim einschläft, und aktiviert latente Akteure. |
| 9 | **Reporting: Sentiment nach Akteurs-Typ** explizit als Pflichtsektion | War nur implizit in v1.0; aus Realtest klar als Lücke erkennbar. |
| 10 | **Reporting: Quoten-Format mit Konfidenzintervall** standardisiert | Aussagen wie "58–65% Pilotinteresse" sollen einheitlich strukturiert werden, nicht freitextlich. |

---

## Inhaltsverzeichnis

1. [Vision und Ziele](#1-vision-und-ziele)
2. [Aktueller Stand und Probleme](#2-aktueller-stand-und-probleme)
3. [Lösungsansatz: Drei-Phasen-Modell](#3-lösungsansatz-drei-phasen-modell)
4. [Akteurs-System](#4-akteurs-system)
5. [Crowd-Layer](#5-crowd-layer)
6. [Plattform-Layer (NEU)](#6-plattform-layer-neu)
7. [Recherche-Modul](#7-recherche-modul)
8. [Verteilungs-System](#8-verteilungs-system)
9. [Template-System](#9-template-system)
10. [Influence-Network-Erweiterung](#10-influence-network-erweiterung)
11. [Reporting-Erweiterung](#11-reporting-erweiterung)
12. [UI-Architektur](#12-ui-architektur)
13. [Datenmodell-Migration](#13-datenmodell-migration)
14. [Implementierungs-Reihenfolge](#14-implementierungs-reihenfolge)
15. [Test-Strategie unter API-Kosten-Constraints](#15-test-strategie-unter-api-kosten-constraints)
16. [Erfolgskriterien](#16-erfolgskriterien)
17. [Offene Designfragen](#17-offene-designfragen)
18. [Risiken und Stolpersteine](#18-risiken-und-stolpersteine)

---

## 1. Vision und Ziele

### 1.1 Vision

Agora soll vom **Demonstrator für AI-gestützte Marktforschung** zu einem **ernstzunehmenden Werkzeug** werden, das reale Märkte differenziert genug abbildet, um vor echten Investitionen valide Hypothesen zu liefern.

Der entscheidende Unterschied zu klassischen Persona-Tools (z.B. Dialego TAIA, The Persona Institute, Toluna HarmonAIze) ist nicht die Persona-Anzahl, sondern die **Multi-Akteurs-Dynamik**: Eine Markteinführung wird nicht nur von Verbrauchern entschieden, sondern von einem Geflecht aus Käufern, Wettbewerbern, Medien, Influencern, Behörden, Instituten, Verbänden, Validierern und Gatekeepern – plus dem anonymen Online-Schwarm und den strukturellen Eigenschaften der Plattformen, auf denen diskutiert wird.

### 1.2 Ziele dieser Erweiterung

| Ziel | Begründung |
|------|------------|
| **Realismus** durch differenzierte Akteurs-Typen | Aktuelles System hat nur 3 Kategorien (organization/individual/institution) – das spiegelt keinen realen Markt wider |
| **Reproduzierbarkeit** durch ausgekoppelte Recherche | Multi-Run-Vergleiche werden erst sinnvoll, wenn der Marktkontext fix ist |
| **Anwendungsbreite** durch Template-System | Eine Sim für Pharma-Launch braucht andere Akteure als eine für B2B-SaaS |
| **Dynamische Sims** durch Trigger und News-Injection | Ohne externe Stimuli stagnieren Sims ab Tag 10 (im Realtest beobachtet) |
| **Ernst genommen werden** durch Validierung gegen reale Markteinführungen | Backtests schaffen Vertrauen bei skeptischen Marktforschern |

### 1.3 Was diese Erweiterung NICHT ist

- Keine Auflösung der Limitation "Personas sind synthetisch" (das bleibt grundsätzlich)
- Keine Ablösung klassischer Marktforschung, sondern Pre-Screening
- Keine Vorhersage konkreter Verkaufszahlen, sondern qualitativer Dynamiken

---

## 2. Aktueller Stand und Probleme

### 2.1 Was Agora heute kann

- Persona-Generierung (10–500 Personas in 3 Kategorien: organization, individual, institution)
- Optionale Web-Recherche (Deep Mode, gekoppelt an Sim-Erstellung)
- Tick-basierte Simulation mit Posts, Kommentaren, Meinungs-Shifts
- Zwei Plattformen (Threadit, Feedbook) – pragmatisch vs. institutionell
- Anti-Echo-Chamber-Mechaniken
- Multi-Run und Stress-Tests
- Confidence-rated Reports
- Methodische Grenzen-Sektion (sehr gut)

### 2.2 Identifizierte Probleme (aus Realtest verifiziert)

**Problem 1: Recherche-Phase ohne User-Kontrolle.** Aktuell wählt das System Quellen (DuckDuckGo) und Synthese-Modell selbst. Der User kann weder Tiefe, Fokus, eigenen Prompt noch eigene Daten einbringen.

**Problem 2: Akteurs-Pool ist zu uniform.** Nur 3 Kategorien; im B2B-Kontext werden FM-Leads als "individual" markiert, obwohl sie funktional eher Experten in beruflicher Rolle sind.

**Problem 3: Anonyme Online-Dynamik fehlt.** Crowd-Layer ist nicht modelliert.

**Problem 4: Keine Reproduzierbarkeit.** Multi-Runs ändern unkontrolliert auch den Marktkontext.

**Problem 5: Konfiguration nur grob.** User kann keine Akteurs-Mischung steuern.

**Problem 6: Sim verliert Momentum (NEU aus Realtest).** Originalbeobachtung im 15-Tage-Test: *"Späte Phasen (Tag 11–15) sind aus Musterfortschreibung abgeleitet."* Ohne neue Stimuli erschöpfen sich die Akteure.

**Problem 7: Validierer fehlen als eigene Klasse (NEU aus Realtest).** TÜV, VdS, BNetzA, Versicherer tauchten in der Sim als kritische Marktteilnehmer auf, die zwar zitiert, aber nie als eigene Akteure modelliert werden.

**Problem 8: Hybride Trägerschaft fehlt (NEU aus Realtest).** AöR und kommunale Akteure passen weder in "Firma" noch in "Behörde".

---

## 3. Lösungsansatz: Drei-Phasen-Modell

Die Sim wird konzeptionell in drei voneinander entkoppelte Phasen aufgeteilt:

```
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│  PHASE 1: Recherche  │ →  │ PHASE 2: Simulation  │ →  │  PHASE 3: Analyse    │
│                      │    │                      │    │                      │
│  - Marktkontext      │    │  - Persona-Generation│    │  - Sentiment-Trends  │
│  - Sozio-Kultur      │    │  - Tick-Loop         │    │  - Influence-Flow    │
│  - Regulatorik       │    │  - Crowd-Dynamik     │    │  - Crowd-Verlauf     │
│  - Wettbewerber      │    │  - Akteurs-Verhalten │    │  - Wendepunkte       │
│  - Mediennarrative   │    │  - Trigger/Injection │    │  - Sentiment-by-Type │
│                      │    │  - Stagnations-Watch │    │  - Quoten-Schätzungen│
└──────────────────────┘    └──────────────────────┘    └──────────────────────┘
       Wiederverwendbar          Mehrere Runs auf            Auch über Multi-Runs
       als Snapshot              gleicher Recherche          aggregierbar
```

**Schlüssel:** Phase 1 wird zum eigenständigen Modul. Phase 2 wird durch Trigger und Plattform-Layer dynamischer.

---

## 4. Akteurs-System

Das Herzstück der Erweiterung. Statt der aktuellen 3 Kategorien (organization/individual/institution) führen wir **9 Akteurs-Typen** plus eine **Crowd-Schicht** ein – alle modulierbar durch **Funktions-Tags** und zusätzliche Dimensionen.

### 4.1 Die 9 Akteurs-Typen (v1.1)

| # | Typ | Was er ist | Kernverhalten | Reichweite | Glaubwürdigkeit |
|---|-----|------------|---------------|------------|-----------------|
| 1 | Privatperson | Einzelne Stimme aus Zielgruppe oder Umfeld | Postet emotional, ändert Meinung | 1× | mittel |
| 2 | Firma | Organisation mit Marktinteresse | Offizielle Statements, vorsichtig | 5–20× | mittel-hoch |
| 3 | Institut/Forschung | Wissenschaftliche Einrichtung | Evidenzbasiert, langsam, zurückhaltend | 10–30× | sehr hoch |
| 4 | Behörde/Regulator | Staatliche Stelle mit Mandat | Formal, regelorientiert, themenspezifisch | 30–100× | sehr hoch |
| 5 | Medium/Journalist | Berichtende Instanz | Neutral-skeptisch, sucht Stories | 50–500× | hoch (Multiplikator) |
| 6 | Influencer | Reichweiten-getriebene Einzelperson | Polarisiert, persönliche Marke | 100–1000× | polarisiert |
| 7 | Experte/Fachperson | Domänen-Autorität | Sachlich, themengebunden | 5–50× | hoch (in Domäne) |
| 8 | Kollektiver Akteur | Verband/NGO/Partei/Kammer/Krankenkasse/Stiftung/Gewerkschaft | Vertritt Gruppeninteresse, mobilisiert | 20–200× | mittel-hoch |
| 9 | **Validierer/Zertifizierer** *(NEU)* | Prüfende Instanz mit Zertifizierungs-Mandat | Postet selten, gibt binäre Signale | 10–50× | sehr hoch (in Domäne) |
| — | Crowd-Layer | Anonymer Schwarm (parallel) | Aggregat aus anonymen Reaktionen | n/a | gering pro Stimme, summierend |

> **Wichtige Änderung gegenüber v1.0:** Gatekeeper ist kein eigener Typ mehr, sondern eine **Funktion** (siehe 4.10).

### 4.2 Profil-Schemata pro Typ

Jeder Typ hat ein eigenes Profil-Schema. Big Five gilt nur für Typen 1, 6, 7. Alle Organisations-Typen (2, 3, 4, 5, 8, 9) haben zusätzlich die Dimension `traegerschaft`.

#### 4.2.1 Privatperson (mit `context`-Dimension)

```yaml
basis:
  id: uuid
  name: string
  actor_type: "private_person"
  context: "privat" | "beruflich" | "oeffentlich"   # NEU v1.1
  stance: dynamisch je nach context
  activation_latency: int (Tage)                     # PFLICHT v1.1
  trigger_condition: optional
  function_tags: [list]                              # NEU v1.1, z.B. "bruckenakteur"
  
profil:
  alter: int
  geschlecht: string
  region: string
  bildung: string
  einkommen: enum
  beruf: string                                      # NEU v1.1, relevant bei context=beruflich
  rolle: string                                      # NEU v1.1, z.B. "FM-Lead", "Einkäufer"
  big_five: {...}
  werte: [list]
  diffusion_phase: enum
```

**Stance-Optionen je context:**
- `context=privat`: endkunde / betroffene / branchenangehoerige
- `context=beruflich`: entscheider / einkaeufer / fachkraft / berater / influencer_intern
- `context=oeffentlich`: buerger / aktivist / kritiker

#### 4.2.2 Firma (mit `traegerschaft`-Dimension)

```yaml
basis:
  ...
  actor_type: "company"
  traegerschaft: "privat" | "oeffentlich" | "genossenschaftlich" | "gemischt" | "kommunal"   # NEU v1.1
  stance: "potential_buyer" | "competitor" | "supplier" | "observer"
  function_tags: [list]                              # z.B. "marktzugangs_gatekeeper"

profil:
  branche: string
  groesse: "klein" | "mittel" | "gross" | "konzern"
  marktposition: string
  rechtsform: string                                 # NEU v1.1: GmbH / AG / AöR / eG / etc.
  risikoaversion: float (0-1)
  markenwerte: [list]
  entscheidungsstruktur: enum
  digitalisierungsgrad: float
```

#### 4.2.3 Institut/Forschung

```yaml
basis:
  ...
  actor_type: "research_institute"
  traegerschaft: "oeffentlich" | "privat" | "gemischt"
  stance: "neutral" | "kritisch" | "befuerwortend"

profil:
  forschungsschwerpunkt: [list]
  reputation: float (0-1)
  finanzierung: enum
  publikations_output: enum
  kooperationen: [list of references]
```

#### 4.2.4 Behörde/Regulator

```yaml
basis:
  ...
  actor_type: "authority"
  traegerschaft: "oeffentlich" (default)
  stance: "neutral" | "regulatorisch_streng" | "marktfreundlich" | "risikoavers"   # erweitert v1.1

profil:
  zustaendigkeit: [list of domains]
  hierarchie_ebene: "kommunal" | "land" | "bund" | "eu"
  politische_ausrichtung: enum
  reaktionsgeschwindigkeit: enum
```

#### 4.2.5 Medium

```yaml
basis:
  ...
  actor_type: "media"
  traegerschaft: "privat" | "oeffentlich" | "gemischt"  # ÖR vs. private Sender
  stance: "boulevard" | "qualitaet" | "fachpresse" | "tendenzfrei"

profil:
  reichweite: int
  format: enum
  politische_tendenz: float (-1 bis +1)
  zielgruppe: string
  fokus: [list of topics]
```

#### 4.2.6 Influencer

```yaml
basis:
  ...
  actor_type: "influencer"
  context: "consumer" | "business" | "politisch"     # NEU v1.1: B2B-Influencer existieren!
  stance: variabel
  function_tags: [list]                              # z.B. "multiplikator", "bruckenakteur"

profil:
  plattform: enum
  reichweite: int (Follower)
  polaritaet: float
  zielgruppe: string
  werbedeals: bool
  big_five: {...}
```

#### 4.2.7 Experte

```yaml
basis:
  ...
  actor_type: "expert"
  stance: "neutral" | "befuerwortend" | "kritisch"

profil:
  domaene: string
  jahre_erfahrung: int
  sichtbarkeit: float
  affiliation: string
  affiliation_type: "firma" | "institut" | "freelance" | "behoerde"   # NEU v1.1
  big_five: {...}
```

#### 4.2.8 Kollektiver Akteur

```yaml
basis:
  ...
  actor_type: "collective"
  subtype: "verband" | "ngo" | "partei" | "kammer" | "krankenkasse" | "stiftung" | "gewerkschaft"
  traegerschaft: "oeffentlich" | "privat" | "gemischt"
  stance: "befuerwortend" | "kritisch" | "ambivalent"
  function_tags: [list]                              # z.B. "meinungs_gatekeeper"

profil:
  mitgliederzahl: int
  mandat: string
  lobbyaktivitaet: enum
  politische_verortung: float (-1 bis +1)
  reichweite_in_branche: float                       # NEU v1.1
```

#### 4.2.9 Validierer/Zertifizierer (NEU v1.1)

Ersetzt den vorherigen Gatekeeper-Typ. Modelliert TÜV, VdS, BNetzA, Versicherer, Eichämter etc.

```yaml
basis:
  ...
  actor_type: "validator"
  subtype: "tuev" | "behoerdliche_pruefstelle" | "versicherer" | "norm_setter" | "eichamt" | "branchen_zertifizierer"
  traegerschaft: "privat" | "oeffentlich" | "gemischt"
  stance: "neutral" (default, ändert sich nur durch Bewertung)

profil:
  pruefdomaene: [list]                               # was wird geprüft
  autoritaet_in_domaene: float (0-1)
  reaktionsgeschwindigkeit: enum                     # i.d.R. langsam
  freigabe_status: "pending" | "approved" | "rejected" | "conditional"   # binäres Hauptsignal
  freigabe_begruendung: text
```

**Besonderes Verhalten:** Validierer posten selten, aber jeder Post ist ein **Hauptsignal**, das von vielen anderen Akteuren zitiert wird. Wenn `freigabe_status = rejected`, wird die Sim für die getroffene Domäne blockiert.

### 4.3 Verhaltens-Parameter pro Typ

| Parameter | Privatp. | Firma | Institut | Behörde | Medium | Influencer | Experte | Kollektiv | **Validierer** |
|-----------|----------|-------|----------|---------|--------|------------|---------|-----------|----------------|
| Posts/Tick (avg) | 0.3 | 0.1 | 0.05 | 0.02 | 0.4 | 0.6 | 0.2 | 0.15 | **0.01** |
| Aktivierungs-Latenz (Tage) | 0–1 | 1–3 | 5–10 | 7–15 | 1–4 | 0–2 | 2–5 | 3–7 | **10–20** |
| Trigger-Schwelle | — | — | 2000 Erw. | 5000 Erw. | 500 Erw. | — | 1000 Erw. | 3000 Erw. | **Anfrage** |
| Reichweiten-Multiplikator | 1× | 5–20× | 10–30× | 30–100× | 50–500× | 100–1000× | 5–50× | 20–200× | **30–100×** |
| Glaubwürdigkeit | 0.5 | 0.6 | 0.9 | 0.85 | 0.7 | 0.4–0.8 | 0.85 | 0.6 | **0.95** |
| Dropout-Rate | 30% | 10% | 5% | 5% | 5% | 5% | 10% | 8% | **2%** |

> **Validierer**: posten extrem selten, aber wenn sie posten, ist der Effekt maximal. Werden meistens durch eine "Anfrage" durch andere Akteure aktiviert.

### 4.4 Aktivierungs-Latenz und Trigger (PFLICHT v1.1)

> **Änderung v1.1:** Latenz und Trigger waren in v1.0 optional. Aufgrund der beobachteten Stagnation ab Tag 10 sind sie jetzt PFLICHT-Felder pro Akteur.

**Latenz** modelliert, wann ein Typ frühestens aktiv wird. Eine Behörde reagiert nicht am Tag 1, sondern wenn ein Thema "auf den Tisch kommt".

**Trigger** sind Schwellenwert-Bedingungen: Akteur wird erst aktiv bei z.B. 5.000 Erwähnungen, oder bei externer News-Injection (siehe 4.11), oder bei Validierer-Anfrage.

Neu: **Verfallsdatum von Aktivierung.** Nach einem Aktivierungs-Spike kühlt ein Akteur wieder ab (modelliert durch `engagement_decay_rate` pro Typ).

### 4.5 Stance/Disposition

Ersetzt die ursprüngliche "Market Role". Ist pro Typ unterschiedlich definiert (siehe Profil-Schemata 4.2). Macht klar, **wie** ein Akteur a-priori zum Produkt steht.

### 4.6 Tonalitäts-Templates

Pro Akteurs-Typ ein **Sprach-DNA-Template**, das in den Generierungs- und Verhaltens-Prompt einfließt. Beispiele:

- **Influencer:** *"Leute, ich hab das Ding jetzt 2 Wochen getestet 🔥..."*
- **Behörde:** *"Im Rahmen der laufenden Marktbeobachtung wurde festgestellt..."*
- **Institut:** *"Eine Vorabauswertung unserer Erhebung deutet darauf hin..."*
- **Validierer:** *"Auf Antrag der [Firma X] wurde am [Datum] geprüft. Ergebnis: ..."*
- **Medium:** *"Während Branchenkenner den Launch begrüßen, mehren sich kritische Stimmen..."*

Templates sind:
- als Default vorgegeben
- vom User duplizierbar und individuell anpassbar
- pro Sim auswählbar (z.B. "Influencer – Tech-Bro" vs. "Influencer – Pharma")

Modulation: Persönlichkeits-Eigenschaften (Alter, Region, Bildung, Kontext) modulieren das Template pro Persona.

### 4.7 Beziehungs-Layer

Optionales Vorab-Setup, das **a-priori-Verbindungen** zwischen Personas modelliert. Im Realtest beobachtet:

> *"ZIA/GdW → kommunale/wohnungswirtschaftliche Akteure: Formale Ablehnungen werden aufgegriffen und lokal 'übersetzt'"*

Datenmodell: separate `actor_relationships`-Tabelle mit Typ-getaggten Edges (kennt, vertraut, konkurriert, zitiert, kaskadiert_von).

Quellen für Beziehungen:
- Manuell vom User gepflegt
- Automatisch aus Recherche-Output abgeleitet (Wettbewerber → Edge "konkurriert")

### 4.8 Persona-Lifecycle

- **Eintritt:** Akteur betritt die Sim erst ab Tag X (Behörden später, Crowd früher)
- **Austritt:** Akteur verliert das Interesse (typischerweise Privatpersonen nach 3–7 Tagen)
- **Reaktivierung:** Trigger oder News-Injection kann Akteur reaktivieren

### 4.9 Lurking/Dropout

In sozialen Dynamiken postet nur ein Bruchteil der Akteure aktiv. Die 75/9/1-Regel:
- 75% der Personas konsumieren nur (lurken)
- 9% reagieren minimal
- 1% postet substantiell

Pro Akteurs-Typ moduliert (siehe Tabelle 4.3).

### 4.10 Funktions-Tag-System (NEU v1.1)

Manche Rollen sind nicht typgebunden. Statt sie als eigene Typen zu führen, werden sie als **Tags** modelliert, die ein Akteur einnehmen kann:

| Tag | Bedeutung | Kann eingenommen werden von |
|-----|-----------|------------------------------|
| `meinungs_gatekeeper` | Position kaskadiert in eine Community | Kollektiver Akteur, Medium, Influencer, Experte |
| `marktzugangs_gatekeeper` | Entscheidet über Listing/Vertrieb | Firma (z.B. Edeka, App-Store), Plattform-Betreiber |
| `bruckenakteur` | Vermittelt zwischen Clustern | jeder Typ |
| `multiplikator` | Hat überdurchschnittliche Reichweite | jeder Typ |
| `polarisierer` | Treibt Meinungs-Spreizung | jeder Typ |
| `early_signal_giver` | Gibt frühzeitig Richtungssignal | jeder Typ |

Tags beeinflussen:
- Reichweiten-Berechnung im Influence-Network
- Auswahl im Reporting (z.B. "Top-3 Brückenakteure")
- Trigger-Logik (z.B. ein `early_signal_giver` postet zu Beginn)

Tags können vom User manuell vergeben oder automatisch aus Recherche/Sim-Verlauf erkannt werden.

### 4.11 News-Injection / Trigger-Events (NEU v1.1)

> **Hintergrund:** Im Realtest verlor die Sim ab Tag 10 Momentum. Lösung: User kann fingierte Events einspeisen, auf die Akteure reagieren.

**Datenmodell:**
```yaml
trigger_event:
  id: uuid
  simulation_id: uuid
  tick_day: int
  event_type: "news_headline" | "competitor_action" | "regulatory_change" | "validator_decision" | "social_incident"
  title: string
  content: text
  affected_segments: [list]                # welche Akteurs-Typen reagieren?
  intensity: "minor" | "major" | "critical"
  source_attribution: string               # "fingierter Spiegel-Online-Artikel" etc.
```

**Beispiele:**
- `event_type=news_headline`, Tag 5: "Spiegel Online berichtet über ChargeBot-Brand in Münchner Tiefgarage"
- `event_type=competitor_action`, Tag 7: "MainCharge launcht stationäre Konkurrenzlösung mit Förderung"
- `event_type=regulatory_change`, Tag 10: "BNetzA kündigt verschärfte Anforderungen an mobile DC-Lader an"
- `event_type=validator_decision`, Tag 12: "TÜV Süd erteilt Pilotfreigabe für ChargeBot M50"

**UI:** Beim Sim-Setup oder während laufender Sim kann der User Events einplanen oder live einwerfen. Sim reagiert in den nächsten Ticks.

### 4.12 Stagnations-Detection mit Auto-Reactivation (NEU v1.1)

Damit der User nicht zwingend Events manuell einspeisen muss, gibt es eine automatische Mechanik:

**Detection:** Pro Tick wird gemessen:
- Posts pro Tick (rollender Durchschnitt)
- Sentiment-Varianz
- Anzahl neuer Argumente

Wenn alle drei unter Schwellenwert fallen → Stagnation erkannt.

**Reactivation:** System aktiviert:
- Latente Akteure mit höchstem Reichweiten-Potenzial
- Zufälliges generiertes News-Event aus konfigurierter Event-Library
- Validierer mit `freigabe_status=pending` werden zur Entscheidung gedrängt

**Konfigurierbar:** User kann pro Sim entscheiden:
- "Nichts tun" (Sim läuft natürlich aus)
- "Auto-Reactivation milde" (1× pro 5 Ticks bei Stagnation)
- "Auto-Reactivation aggressiv" (jeden 2. Tick neue Stimuli)

---

## 5. Crowd-Layer

Parallele Schicht zur Akteurs-Ebene, modelliert das anonyme Hintergrundrauschen.

### 5.1 Was die Crowd ist

Die Crowd ist **keine Sammlung von Personas**, sondern ein **statistisches Aggregat** pro Plattform und Tick:

```yaml
crowd_state:
  platform_id: uuid                        # Referenz auf Plattform-Layer (NEU v1.1)
  tick: int
  volume: int (Anzahl Reaktionen)
  sentiment: float (-1 bis +1)
  polarization: float (0 bis 1)
  momentum: float (Veränderungsrate)
  representative_voices: [list of short strings]
```

### 5.2 Mechaniken

#### 5.2.1 Crowd reagiert auf Akteure
Wenn ein namhafter Akteur postet:
- Influencer-Post → starke Crowd-Reaktion
- Behörden-/Validierer-Statement → polarisierende Reaktion
- Medien-Bericht → volumen-treibende Reaktion

#### 5.2.2 Crowd wirkt auf Personas (Bandwagon-Effekt)
Personas sehen Crowd-Aggregat und passen ihre Meinung graduell an.

#### 5.2.3 Crowd verstärkt sich selbst
Bei kritischer Masse beginnt Echo-Kammer-Effekt – Mechanismus hinter Shitstorms.

#### 5.2.4 Repräsentative Stimmen
Pro Tick einige beispielhafte anonyme Reaktionen für Visualisierung.

### 5.3 Crowd im UI

- Eigene Dashboard-Komponente: Crowd-Mood-Verlauf über Zeit
- Pro Plattform getrennt darstellbar
- Im Report eigener Abschnitt mit Wendepunkten
- "Chat mit Crowd" zeigt aggregierte Stimmung

---

## 6. Plattform-Layer (NEU v1.1)

> **Hintergrund:** Das aktuelle System hat bereits Threadit/Feedbook implizit. Im Realtest zeigte sich klar, dass Plattformen unterschiedlichen Charakter haben (operativ-pragmatisch vs. institutionell-juristisch). Diese Erkenntnis wird zu einer formalen Schicht ausgebaut.

### 6.1 Was eine Plattform ist

Eine Plattform ist ein **Diskussions-Raum** mit eigenen Eigenschaften, kein Akteur. Beispiele aus dem Realtest:

- **Threadit:** operativ-pragmatisch, KPI-fokussiert, hohes Engagement
- **Feedbook:** institutionell-juristisch, formal, langsamer

Erweiterungen denkbar:
- **Newsfeed:** boulevardesk, virale Schlagzeilen
- **Fachforum:** Experten-zentriert, sachlich
- **Öffentliche Petition:** Bürger-Mobilisierung

### 6.2 Plattform-Schema

```yaml
platform:
  id: uuid
  name: string
  character: "operativ" | "institutionell" | "boulevard" | "fachlich" | "oeffentlich"
  tonality_modifier: text                  # ergänzt Persona-Tonalität
  reach_multiplier: float                  # Posts hier wirken Faktor X
  preferred_actor_types: [list]            # welche Typen sind hier dominant
  echo_chamber_strength: float (0-1)       # wie stark verstärkt sich Konsens
  default_engagement_rate: float
```

### 6.3 Akteurs-Plattform-Affinität

Jeder Akteurs-Typ hat default-Affinitäten zu Plattformen:

| Typ | Threadit | Feedbook | Newsfeed | Fachforum |
|-----|----------|----------|----------|-----------|
| Privatperson (privat) | mittel | niedrig | hoch | niedrig |
| Privatperson (beruflich) | hoch | mittel | niedrig | hoch |
| Firma | hoch | hoch | niedrig | mittel |
| Behörde | niedrig | hoch | mittel | niedrig |
| Medium | mittel | mittel | hoch | niedrig |
| Influencer | hoch | niedrig | hoch | niedrig |
| Experte | hoch | mittel | niedrig | hoch |
| Kollektiver Akteur | mittel | hoch | mittel | niedrig |
| Validierer | niedrig | hoch | niedrig | hoch |

### 6.4 Cross-Posting

Akteure können auf mehreren Plattformen aktiv sein. Im Realtest beobachtet:
> *"Cross-Posting einzelner Operator erhöht Reichweite, ändert aber die Grundhaltung der Verbände kaum"*

→ Cross-Posting ist möglich, aber jede Plattform hat ihre eigene Dynamik.

### 6.5 User-Konfiguration

Beim Sim-Setup kann der User:
- Plattformen aktivieren/deaktivieren
- Eigene Plattformen anlegen (Custom)
- Affinitäten anpassen pro Sim

---

## 7. Recherche-Modul

Eigenes Sidebar-Modul für die Erstellung und Verwaltung von Marktrecherchen.

### 7.1 Multi-Pass-Pipeline

Statt einem LLM-Call eine strukturierte Pipeline mit fünf Pässen:

| Pass | Inhalt | Beispiel-Prompt |
|------|--------|-----------------|
| 1. Markt | Branchengröße, Trends, Wachstum | "Beschreibe den Markt für [Produkt] in [Region], inkl. Größe, Wachstum, Hauptakteure" |
| 2. Sozio-Kultur | Werte, Lebensstile, dominante Narrative | "Welche kulturellen Werte und Lebensstile sind bei der Zielgruppe [X] aktuell dominant?" |
| 3. Regulatorik | Gesetze, Standards, anstehende Änderungen | "Welche Gesetze und Vorschriften betreffen [Produkt] in [Region]?" |
| 4. Wettbewerber | Direkte und indirekte Konkurrenz | "Wer sind die Hauptwettbewerber für [Produkt] in [Region]?" |
| 5. Mediennarrative | Aktuelle Berichterstattung, dominante Frames | "Wie wird [Thema] aktuell in deutschen Medien diskutiert?" |

Jeder Pass: eigener Prompt, eigenes LLM/Modell, eigene Quellen-Strategie.

### 7.2 Recherche als Snapshot

Output wird als JSON gespeichert:
```yaml
research_snapshot:
  id: uuid
  name: string
  created_at: datetime
  llm_used: string
  passes:
    markt: { content, sources, confidence }
    sozio_kultur: { content, sources, confidence }
    regulatorik: { content, sources, confidence }
    wettbewerber: { content, sources, confidence }
    mediennarrative: { content, sources, confidence }
  status: "draft" | "approved" | "archived"
```

### 7.3 Wiederverwendung

- Recherche kann an mehrere Sims angehängt werden
- Multi-Run nutzt automatisch die gleiche Recherche
- Recherche kann versioniert werden

### 7.4 Einspeisung in die Simulation

- Wettbewerber-Liste → Akteurs-Typ "Firma" mit Stance "competitor"
- Regulatorische Akteure → Akteurs-Typ "Behörde"
- Validierer-Hinweise → Akteurs-Typ "Validator" (NEU v1.1)
- Mediennarrative → System-Prompts für Personas
- **Vorgeschlagene Trigger-Events** → Liste von Events, die User für News-Injection nutzen kann (NEU v1.1)

---

## 8. Verteilungs-System

UI für die Konfiguration der Akteurs-Mischung pro Sim.

### 8.1 Drei Verteilungs-Ebenen

1. **Typ-Verteilung:** Wie viel Prozent welcher Akteurs-Typ?
2. **Subtyp-Verteilung:** Innerhalb Kollektive Akteure / Validierer
3. **Stance-/Context-Verteilung:** Innerhalb Firmen, Privatpersonen etc.

### 8.2 Verteilungs-Templates (Defaults v1.1)

| Template | Privatp. | Firma | Institut | Behörde | Medium | Influencer | Experte | Kollektiv | **Validierer** |
|----------|----------|-------|----------|---------|--------|------------|---------|-----------|----------------|
| B2C-Konsum | 75% | 5% | 0% | 2% | 5% | 8% | 3% | 2% | — |
| B2B-Software | 10% | 50% | 5% | 5% | 5% | 5% | 12% | 5% | **3%** |
| **B2B-Industriegut** *(NEU)* | 10% | 40% | 5% | 8% | 5% | 3% | 15% | 7% | **7%** |
| Forschungskampagne | 5% | 22% | 35% | 15% | 10% | — | 8% | 3% | **2%** |
| Politische Initiative | 30% | 5% | 5% | 15% | 23% | 5% | 5% | 10% | **2%** |
| Healthcare/Pharma | 22% | 13% | 20% | 13% | 10% | 5% | 8% | 4% | **5%** |
| Finanz | 28% | 22% | 5% | 13% | 10% | 5% | 8% | 4% | **5%** |

> Die Realtest-Sim entspricht "B2B-Industriegut" – mit korrekter Verteilung wären Validierer (TÜV, VdS, BNetzA) eigene Akteure gewesen.

### 8.3 Optional: Zeitkurve

Statt fixer Verteilung kann die Mischung über die Sim-Zeit variieren. Implementiert als Verlaufskurve pro Akteurs-Typ.

---

## 9. Template-System

Übergreifendes System für drei Template-Kategorien.

### 9.1 Pattern

```yaml
template:
  id: uuid
  category: "research" | "distribution" | "tonality" | "trigger_library"   # erweitert v1.1
  name: string
  owner: user_id | "system"
  is_default: bool
  content: json
  version: int
  parent_id: optional
```

### 9.2 Vier Template-Kategorien (v1.1)

| Kategorie | Inhalt | Default-Anzahl |
|-----------|--------|----------------|
| Recherche-Templates | 5 Pass-Prompts pro Template | 6 (B2C, B2B, Forschung, Politik, Pharma, Finanz) |
| Verteilungs-Templates | Prozent-Mischung pro Typ | 7 (siehe 8.2) |
| Tonalitäts-Templates | Sprach-DNA pro Akteurs-Typ | 9 Defaults (1 pro Typ) |
| **Trigger-Library** *(NEU v1.1)* | Vorgefertigte News-Events pro Branche | 6 Sets (analog zu Recherche-Templates) |

### 9.3 Branchen-Pakete (Power-Feature)

Ein Branchen-Paket bündelt:
- 1× Recherche-Template
- 1× Verteilungs-Template
- 9× Tonalitäts-Templates
- 1× Trigger-Library (NEU v1.1)

Beispiele: "Heizungsbau-DE", "B2B-SaaS", "Pharma", "Politik", "E-Mobility-DACH".

### 9.4 Export/Import (V2)

Templates und Pakete als JSON exportierbar/importierbar.

---

## 10. Influence-Network-Erweiterung

### 10.1 Edge-Gewichtung nach Akteurs-Typ

```
Edge.weight = base_weight 
            × source.reach_multiplier 
            × source.credibility_for_topic 
            × target.openness_to_source_type
            × platform.reach_multiplier         # NEU v1.1
            × function_tag_modifier             # NEU v1.1
```

### 10.2 Reichweite und Glaubwürdigkeit

Pro Akteurs-Typ definiert (siehe Tabelle 4.3). Themen-Spezifität: Behörde/Validierer haben hohe Glaubwürdigkeit nur in ihrer Zuständigkeit.

### 10.3 Beziehungs-Edges (a-priori)

Vor Sim-Start setzbare Edges. Aus Realtest: ZIA → kommunale Akteure als Kaskaden-Edge.

### 10.4 Visualisierung

Influence-Flow zeigt im Report:
- Welcher Akteur hat wie viele andere verschoben?
- Welche Multiplikator-Effekte sind aufgetreten?
- Welche Brückenakteure gab es?
- Pro Plattform getrennt darstellbar (NEU v1.1)

---

## 11. Reporting-Erweiterung

### 11.1 Pflicht-Sektionen (v1.1)

- **Sentiment differenziert nach Akteurs-Typ** (war v1.0 implizit, jetzt PFLICHT)
- Sentiment differenziert nach Segment (klassisch)
- Stance-Aufschlüsselung pro Typ
- Influence-Flow mit Multiplikator-Effekten
- Crowd-Verlauf pro Plattform
- Plattform-Vergleich (NEU v1.1)
- Wendepunkt-Detection mit Kausalzuordnung
- Validierer-Status (NEU v1.1: "TÜV: pending", "VdS: approved")
- Beziehungs-Effekte (falls Beziehungs-Layer aktiv)
- Trigger-Event-Wirkung (NEU v1.1: "News-Injection an Tag 5 verschob Sentiment um -0.3")

### 11.2 Quoten-Format mit Konfidenzintervall (NEU v1.1)

> **Hintergrund:** Im Realtest stand "58–65% Pilotinteresse" als Freitextschätzung. Das wird standardisiert.

Format pro Quoten-Aussage:
```
Segment: Parkhausketten
Aussage: Pilot-Interesse
Wert: 61% [KI 58–65%]
Stichprobe: 35 Akteure
Konfidenz: MITTEL
Begründung: Diskursdichte, keine Vollerhebung
```

UI: Tabelle pro Segment mit allen Quoten-Aussagen.

### 11.3 Multi-Run-Vergleich (drei Modi)

| Modus | Was bleibt gleich | Was variiert | Beantwortet |
|-------|-------------------|--------------|-------------|
| Stabilitäts-Run | Alles | Nur Random-Seeds | Wie stabil ist das Ergebnis? |
| Sensitivitäts-Run | Alles bis auf 1 Variable | Eine Variable systematisch | Welcher Effekt hat Variable X? |
| Szenario-Vergleich | Recherche, Produkt | Akteurs-Verteilungen | Was wäre wenn? |

### 11.4 Confidence-Ratings differenziert

Pro Sektion eigene Konfidenz: "Behörden-Reaktion ist [LOW CONFIDENCE]" (bei nur 1 Akteur dieses Typs).

### 11.5 Methodische Grenzen-Sektion

Bleibt 1:1 wie aktuell – im Realtest als sehr stark identifiziert.

---

## 12. UI-Architektur

### 12.1 Sidebar-Struktur (neu)

```
┌─────────────────────┐
│  Simulationen       │  Liste, Status, schneller Zugriff
│  Neue Simulation    │  Wizard (Quick-Start oder Power)
│  Recherche          │  Eigenes Modul
│  Templates          │  4 Kategorien (NEU v1.1)
│  Trigger-Library    │  NEU v1.1 (kann unter Templates)
│  Einstellungen      │  Provider, Defaults
└─────────────────────┘
```

### 12.2 Quick-Start vs. Power

**Quick-Start:** 3 Eingaben (Produkt, Markt, Größe) → alles auf Defaults inkl. Stagnations-Auto-Reactivation.
**Power-Modus:** Vollkonfiguration mit Verteilungs-Editor, Tonalitäts-Auswahl, Recherche-Zuweisung, Trigger-Planung etc.

### 12.3 Persona-Card-System

Generic Component, die typ-spezifische Inhalte rendert. Für alle 9 Typen + Crowd. Chat-Button für alle aktiv.

### 12.4 Trigger-Editor (NEU v1.1)

Beim Sim-Setup oder während laufender Sim:
- Zeitachse mit Tag 1–N
- Drag-and-Drop für Trigger-Events aus Library
- Inline-Editor für Custom-Events
- Vorschau "Welche Akteure würden reagieren?"

### 12.5 Plattform-Editor (NEU v1.1)

In Einstellungen:
- Liste vordefinierter Plattformen (Threadit, Feedbook, Newsfeed, Fachforum)
- Aktivieren/Deaktivieren
- Custom-Plattform anlegen
- Affinitäten anpassen

### 12.6 Onboarding

- Tour beim ersten Login (5 Reiter erklärt in 90 Sekunden)
- Beispiel-Sim als Demo (vorgenerierter Output, kein API-Verbrauch)
- Tooltip-Hinweise

---

## 13. Datenmodell-Migration

### 13.1 Geänderte Tabellen (v1.1)

**`personas`** (Erweiterung):
- `actor_type` (enum, NOT NULL)
- `subtype` (string, nullable)
- `context` (string, nullable, für private_person und influencer) — NEU v1.1
- `traegerschaft` (string, nullable, für Organisations-Typen) — NEU v1.1
- `stance` (string, NOT NULL)
- `activation_latency` (int, NOT NULL, default je Typ) — Pflicht v1.1
- `trigger_condition` (json, nullable)
- `function_tags` (string[], default []) — NEU v1.1
- `engagement_decay_rate` (float, default je Typ) — NEU v1.1
- `profile_data` (json, NOT NULL)

**Neu: `actor_relationships`**:
- `id`, `source_persona_id`, `target_persona_id`, `relation_type`, `weight`, `simulation_id`

**Neu: `crowd_state`**:
- `id`, `simulation_id`, `tick`, `platform_id`, `volume`, `sentiment`, `polarization`, `momentum`, `representative_voices`

**Neu: `research_snapshots`**:
- `id`, `name`, `owner_id`, `created_at`, `llm_used`, `passes` (json), `status`

**Neu: `templates`**:
- `id`, `category`, `name`, `owner_id`, `is_default`, `content` (json), `version`, `parent_id`

**Neu: `platforms`** (v1.1):
- `id`, `name`, `character`, `tonality_modifier`, `reach_multiplier`, `preferred_actor_types`, `echo_chamber_strength`

**Neu: `trigger_events`** (v1.1):
- `id`, `simulation_id`, `tick_day`, `event_type`, `title`, `content`, `affected_segments`, `intensity`, `source_attribution`

**Neu: `validator_decisions`** (v1.1):
- `id`, `validator_persona_id`, `simulation_id`, `tick_day`, `freigabe_status`, `freigabe_begruendung`

### 13.2 Migrationsstrategie

1. Bestehende Personas werden in der Migration zu `actor_type` gemappt:
   - `organization` → `company` (Default)
   - `individual` → `private_person` mit `context=privat` (Default)
   - `institution` → `collective` mit Subtype-Heuristik
2. Bestehende Profil-Daten ziehen in `profile_data` JSON-Feld
3. Bestehende Sims funktionieren weiter (Backward-Compat)
4. Default-Plattformen Threadit/Feedbook werden aus Code in DB überführt

### 13.3 Alembic-Schritte

1. Schema-Erweiterung in einer Migration
2. Daten-Migration in separater Migration
3. Constraint-Hinzufügung erst nach Daten-Migration
4. Neue Tabellen (platforms, trigger_events, validator_decisions) in eigener Migration

---

## 14. Implementierungs-Reihenfolge

### 14.1 Empfohlene Reihenfolge

```
Phase 0: Konzept & Architektur          [1-2 Wochen]
   ↓
Phase 1: Akteurs-System (Herzstück)     [3-4 Wochen]   ← KRITISCH
   ├── inkl. Funktions-Tags, Trägerschaft, Context
   ├── inkl. Validierer-Typ
   ├── inkl. Trigger-System (PFLICHT v1.1)
   └── inkl. Stagnations-Detection
   ↓
   ├──→ Phase 2: Crowd-Layer            [2 Wochen]
   ├──→ Phase 4: Verteilungs-UI         [1-2 Wochen]
   ├──→ Phase 5: Influence-Network      [1-2 Wochen]
   └──→ Phase 9: Plattform-Layer        [1-2 Wochen, NEU v1.1]
   
Parallel zu Phase 1:
   Phase 3: Recherche-Modul              [2 Wochen]
   ↓
Phase 6: Reporting-Erweiterung          [1-2 Wochen, +1 Woche für v1.1]
   ↓
Phase 7: Template-System                [1-2 Wochen]
   ↓
Phase 8: Polish, Onboarding, Validierung [1-2 Wochen]
```

### 14.2 Prioritäten innerhalb Phase 1

Innerhalb des Akteurs-Systems hat höchste Priorität:

1. **Trigger-System + Stagnations-Detection** (löst Realtest-Hauptproblem)
2. **Validierer-Typ** (war im Realtest deutlich erkennbare Lücke)
3. **Context-Dimension auf Privatperson** (B2B-Tauglichkeit)
4. **Trägerschaft-Dimension** (öffentliche Akteure)
5. Restliche Typen-Schemata
6. Tonalitäts-Templates
7. Beziehungs-Layer (kann V2)

### 14.3 Realistische Gesamtzeit

Für Solo-Entwicklung mit AI-Assistenz: **realistisch 3–5 Monate** bis V1 produktreif.

---

## 15. Test-Strategie unter API-Kosten-Constraints

### 15.1 Grundprinzip: "Dry Build, Wet Validate"

| Schicht | API-Bedarf | Vorgehen |
|---------|------------|----------|
| Schema, DB, Migrations | keiner | klassische Unit-Tests, freie Entwicklung |
| Datenmodelle, Validierung | keiner | Pydantic-Tests, freie Entwicklung |
| UI gegen Mock-Daten | keiner | Storybook/Cypress mit Fixtures |
| Prompt-Design | keiner | Prompts in Markdown reviewen |
| Tick-Loop-Algorithmik | keiner | Pure-Function-Tests mit Mock-Antworten |
| Trigger-System | keiner | Reine Event-Logik, deterministisch testbar |
| Punktuelle Integration | minimal | einzelne Calls mit Fast-Tier |
| Voll-Sim-Tests | hoch | nur an Meilensteinen, mit Mini-Sample |

### 15.2 Mock-Modus als zentrales Werkzeug

```python
if settings.MOCK_MODE:
    return load_fixture(f"mock_responses/{prompt_hash}.json")
else:
    return await anthropic_client.create(...)
```

- Alle LLM-Calls deterministisch
- UI durchklickbar ohne API-Verbrauch
- Tick-Loop läuft mit pre-canned Posts/Reactions
- Aktivierbar via `MOCK_MODE=true`

### 15.3 Sparsame Voll-Sim-Tests

| Parameter | Test-Wert | Default-Wert | Ersparnis |
|-----------|-----------|--------------|-----------|
| Persona-Anzahl | 5–10 | 200 | 95% |
| Tick-Anzahl | 3–5 | 30 | 85% |
| Modell | Haiku/GPT-mini | Sonnet/GPT-5 | 80–90% |
| Recherche-Pässe | 1 (statt 5) | 5 | 80% |

### 15.4 Caching identischer Anfragen

- Hash über (Prompt + Modell) als Cache-Key
- Antworten in `dev_cache/` gespeichert
- Cache-Invalidierung manuell

### 15.5 Token-Tracking

- Token-Verbrauch pro Sim loggen
- Geschätzte Kosten anzeigen
- Warnung bei Überschreitung von Budget

### 15.6 Stages

```
dev      → Mock-Modus, kein API
preview  → Mini-Sim mit Fast-Tier (~0,10 €)
release  → Voll-Sim mit Smart-Tier (~5–20 €)
```

### 15.7 Nächster geplanter Realtest (5–10 Tage)

Bei der nächsten Realtest-Sim sollten gezielt geprüft werden:
- [ ] Sentiment nach Akteurs-Typ wird korrekt im Report ausgewiesen
- [ ] Validierer (TÜV/VdS) tauchen als eigene Akteure auf
- [ ] Privatperson-Context (beruflich) wird bei FM-Leads gesetzt
- [ ] Mindestens ein Trigger-Event wird eingespeist und Wirkung gemessen
- [ ] Stagnations-Detection feuert (oder beweist, dass keine Stagnation eintritt)
- [ ] Plattform-Vergleich Threadit/Feedbook ist explizit im Report

---

## 16. Erfolgskriterien

### 16.1 Funktional

- [ ] Alle 9 Akteurs-Typen + Crowd-Layer + Plattform-Layer implementiert
- [ ] Recherche-Modul eigenständig nutzbar und an Sims anhängbar
- [ ] Verteilungs-Editor mit mind. 7 Templates (inkl. B2B-Industriegut)
- [ ] Tonalitäts-Templates pro Typ
- [ ] Trigger-System mit News-Injection und Auto-Reactivation
- [ ] Multi-Run mit den drei Modi
- [ ] Quick-Start funktioniert in <5 Minuten

### 16.2 Qualitativ

- [ ] Mind. 3 Backtests gegen reale Markteinführungen
- [ ] Beta-Tester (mind. 5) bestätigen, dass die Reports realistischer wirken als V0
- [ ] Mock-Modus funktioniert vollständig
- [ ] **Zweite Realtest-Sim zeigt keine Stagnation mehr** (NEU v1.1, Hauptkriterium)

### 16.3 Wirtschaftlich

- [ ] Eine Voll-Sim kostet weniger als 25 € im Smart-Tier
- [ ] Token-Anzeige im UI stimmt mit echter Rechnung überein (±10%)
- [ ] Caching reduziert Entwicklungs-API-Kosten um >50%

### 16.4 Dokumentation

- [ ] README aktualisiert
- [ ] Doku-Ordner mit Akteurs-Erklärungen
- [ ] Mind. 3 Beispiel-Workflows beschrieben

---

## 17. Offene Designfragen

### 17.1 Polymorphes Schema vs. JSON-Spalte
**Empfehlung:** JSON-Spalte mit Pydantic-Validierung in der App-Schicht.

### 17.2 Crowd als Layer oder als Akteurs-Typ?
**Entschieden v1.1:** Eigene Schicht (Layer).

### 17.3 Beziehungs-Layer optional oder Pflicht?
**Empfehlung:** Optional in V1, Pflicht in V2.

### 17.4 Tonalitäts-Templates pro Sim oder global?
**Entschieden:** Global pro User mit eigenen Templates.

### 17.5 Persona-Anzahl-Skalierung
**Empfehlung:** Mindest-Bucket-Größe von 3 Personas pro aktivem Typ. UI warnt bei Unterschreitung.

### 17.6 Sprache der generierten Inhalte
**Empfehlung:** Sim-Einstellung (Sprache global), Template-Parameter (Tonalität pro Typ in dieser Sprache).

### 17.7 Trigger-Library als System-Default oder User-pflegt? (NEU v1.1)
**Empfehlung:** Hybrid – System-Default-Library pro Branche + User kann erweitern und eigene anlegen.

### 17.8 Stagnations-Schwelle dynamisch oder fix? (NEU v1.1)
**Empfehlung:** Drei vordefinierte Profile (mild/normal/aggressiv), kein Slider – sonst überfordert.

### 17.9 Cross-Posting zwischen Plattformen automatisch oder manuell? (NEU v1.1)
**Empfehlung:** Akteurs-Typ entscheidet. Influencer und Medien cross-posten automatisch zu mehreren Plattformen, andere Typen primär auf 1.

---

## 18. Risiken und Stolpersteine

### 18.1 Architektur-Risiken

**Risiko: UI-Komplexität explodiert.**
**Gegenmaßnahme:** Quick-Start als Default, Power-Modus klar abgegrenzt, Trigger-Editor ist eigene Detail-Ansicht.

**Risiko: Persona-Generierung wird zu langsam.**
**Gegenmaßnahme:** Parallelisierung pro Typ, Token-Budget pro Persona begrenzen.

**Risiko: Multi-Pass-Recherche wird teuer.**
**Gegenmaßnahme:** Pro Pass eigenes Modell wählbar, Defaults auf Fast-Tier.

**Risiko: Trigger-System überschreibt natürliche Sim-Dynamik.**
**Gegenmaßnahme:** Trigger immer optional, Stagnations-Detection nur einschalten wenn gewünscht. User soll natürliche Sims durchlaufen lassen können.

**Risiko: Plattform-Layer wird zu komplex.**
**Gegenmaßnahme:** Default-Plattformen (Threadit/Feedbook) sind ausreichend für 90% der Sims. Custom-Plattformen sind Power-Feature.

### 18.2 Wirtschaftliche Risiken

**Risiko: API-Kosten explodieren während Entwicklung.**
**Gegenmaßnahme:** Mock-Modus als Default, Caching, sparsame Voll-Tests.

**Risiko: Sim-Kosten für End-User zu hoch.**
**Gegenmaßnahme:** Auto-Tier-Switching, Token-Anzeige, Modell-Wahl pro Phase.

### 18.3 Konzeptionelle Risiken

**Risiko: Akteurs-Typen klingen am Ende doch alle gleich.**
**Gegenmaßnahme:** Tonalitäts-Templates + Persönlichkeits-Modulation + manuelle Validierung.

**Risiko: Crowd-Layer wird zur Black Box.**
**Gegenmaßnahme:** Klare Visualisierung, "Chat mit Crowd"-Funktion, Beispiele.

**Risiko: Validierer dominieren die Sim zu stark.**
**Gegenmaßnahme:** Validierer haben hohe Wirkung pro Post, aber sehr niedrige Posting-Frequenz und Trigger-Bedingung.

**Risiko: News-Injection wird missbraucht (User "designt" gewünschtes Ergebnis).**
**Gegenmaßnahme:** Im Report wird klar ausgewiesen, welche Trigger-Events eingespeist wurden. Audit-Trail.

### 18.4 Nutzungs-Risiken

**Risiko: User überfordert wegen zu vieler Optionen.**
**Gegenmaßnahme:** Quick-Start, Branchen-Pakete, Tour beim Onboarding.

**Risiko: User missbraucht Sim als Ersatz für echte Marktforschung.**
**Gegenmaßnahme:** "What Agora Is NOT"-Sektion prominent, Confidence-Ratings, Disclaimer.

---

## Anhang A: Glossar (v1.1)

| Begriff | Definition |
|---------|------------|
| Akteur | Sammelbegriff für alle 9 Typen |
| Stance | A-priori-Haltung eines Akteurs zum Produkt |
| Context (NEU) | Persönlicher Lebenskontext (privat/beruflich/öffentlich) bei Privatpersonen |
| Trägerschaft (NEU) | Eigentümerstruktur (privat/öffentlich/genossenschaftlich/gemischt/kommunal) bei Organisationen |
| Funktions-Tag (NEU) | Rolle, die ein Akteur einnehmen kann (z.B. Brückenakteur, Multiplikator) |
| Latenz | Anzahl Tage, bis ein Akteur frühestens aktiv wird |
| Trigger | Schwellenwert-Bedingung, die einen Akteur aktiviert |
| News-Injection (NEU) | Vom User eingespeistes Event, auf das Akteure reagieren |
| Stagnations-Detection (NEU) | Mechanik, die einschlafende Sims erkennt und reaktiviert |
| Validierer (NEU) | Akteurs-Typ #9: Prüfende Instanz mit Zertifizierungs-Mandat |
| Crowd | Aggregierte anonyme Schwarmstimme (kein Akteur) |
| Plattform-Layer (NEU) | Strukturelle Schicht für Diskussions-Räume (Threadit, Feedbook etc.) |
| Tick | Ein Simulationsschritt (typischerweise 1 Tag) |
| Snapshot | Gespeicherte Recherche zur Wiederverwendung |
| Branchen-Paket | Bündel aus Recherche- + Verteilungs- + Tonalitäts-Templates + Trigger-Library |

## Anhang B: Referenzen auf Issues

| Abschnitt | Zugehörige Epics |
|-----------|------------------|
| 4. Akteurs-System | EPIC #1 (mit v1.1-Erweiterungen) |
| 5. Crowd-Layer | EPIC #2 |
| 6. Plattform-Layer (NEU) | EPIC #9 (NEU v1.1) |
| 7. Recherche-Modul | EPIC #3 |
| 8. Verteilungs-System | EPIC #4 |
| 9. Template-System | EPIC #7 |
| 10. Influence-Network | EPIC #5 |
| 11. Reporting | EPIC #6 (mit v1.1-Erweiterungen) |
| 12. UI-Architektur | EPIC #8 |
| 15. Test-Strategie | querschnittlich |

## Anhang C: Realtest-Validierung (NEU v1.1)

Diese Architekturversion basiert auf einer realen 15-Tage-Sim:
- **Produkt:** ChargeBot M50 (autonomer mobiler DC-Lader, B2B DACH)
- **Personas:** 200 (67 organization, 67 individual, 66 institution im alten Schema)
- **Posts:** 1.169
- **Influence-Ereignisse:** 2.038

**Bestätigte Architektur-Entscheidungen:**
- Stance-Logik (Wohnungswirtschaft bleibt durchgehend ablehnend, Parkhauskette pragmatisch)
- Beziehungs-Kaskaden (ZIA → kommunale Akteure)
- Plattform-Differenzierung (Threadit operativ vs. Feedbook institutionell)
- Reichweiten-Multiplikatoren (279 Reaktionen vs. 21 in derselben Sim)

**Identifizierte Anpassungen für v1.1:**
- Validierer-Typ (TÜV, VdS, BNetzA fehlten als eigene Akteure)
- Trägerschaft-Dimension (AöR-Akteure passten nicht in Schema)
- Privatperson-Context (FM-Leads waren als "individual" markiert)
- Trigger-Pflicht (Sim verlor Momentum ab Tag 10)
- Sentiment-by-Type im Report (war nicht enthalten)
- Quoten-Format mit Konfidenzintervall

---

**Ende des Dokuments. Bitte v1.1-Änderungen reviewen, dann Issues abarbeiten.**
