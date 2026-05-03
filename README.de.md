<p align="center">
  <img src="docs/images/agora-logo.png" alt="Agora Logo" width="120">
</p>

<h1 align="center">Agora</h1>

<p align="center">
  <strong>Der virtuelle Marktplatz der Meinungen</strong><br>
  KI-Personas debattieren dein Produkt — bevor du echtes Geld in Marktforschung investierst.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Angular-21-red?logo=angular&logoColor=white" alt="Angular">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/LLM-Claude%20%7C%20GPT%20%7C%20Ollama-8A2BE2" alt="LLM">
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> &middot;
  <a href="#features">Features</a> &middot;
  <a href="#so-funktioniert-es">So funktioniert es</a> &middot;
  <a href="#api">API</a> &middot;
  <a href="#konfiguration">Konfiguration</a> &middot;
  <a href="README.md">English</a>
</p>

---

## Das Problem

Marktforschung ist teuer, langsam und oft nicht aussagekräftig genug. Fokusgruppen kosten fünfstellig, dauern Wochen und liefern Meinungen von 12 Personen. Umfragen erreichen Hunderte, aber messen nur was Leute *sagen* — nicht wie sie *diskutieren, zweifeln und sich gegenseitig überzeugen*.

## Die Lösung

**Agora** simuliert eine virtuelle Gesellschaft: Hunderte KI-Personas mit individuellen Persönlichkeiten, Werten und Meinungen reagieren auf dein Produkt. Sie posten, kommentieren, streiten, ändern ihre Meinung — oder bleiben skeptisch. Am Ende erhältst du einen Analyse-Report mit Konfidenz-Bewertung, der dir sagt **was funktioniert, was nicht, und wie sicher wir uns dabei sind**.

> *Wie auf der antiken Agora versammeln sich hier Stimmen aus allen Schichten — Befürworter, Skeptiker, Experten, Institutionen — und bilden emergente Meinungsdynamiken.*

<!-- SCREENSHOT: Dashboard Overview -->
<p align="center">
  <img src="docs/images/screenshot-dashboard.png" alt="Agora Dashboard" width="800">
</p>

### Screenshots

<details>
<summary><strong>Übersicht — Live-KPIs & Marktkontext</strong></summary>
<p>
  <img src="docs/images/screenshot-overview-1.png" alt="Übersicht mit Marktkontext" width="800">
  <img src="docs/images/screenshot-overview-2.png" alt="KPI-Karten" width="800">
  <img src="docs/images/screenshot-overview-4.png" alt="Stimmungsverteilung" width="800">
</p>
</details>

<details>
<summary><strong>Personas — 200 KI-Agenten mit individuellen Profilen</strong></summary>
<p>
  <img src="docs/images/screenshot-personas.png" alt="Persona-Liste & Detail" width="800">
  <img src="docs/images/screenshot-personas-2.png" alt="Persona Radar-Chart" width="800">
</p>
</details>

<details>
<summary><strong>Netzwerk — Force-Directed Interaktionsgraph</strong></summary>
<p>
  <img src="docs/images/screenshot-network-2.png" alt="Netzwerk-Graph" width="800">
  <img src="docs/images/screenshot-network-3.png" alt="Netzwerk Detail" width="800">
</p>
</details>

<details>
<summary><strong>Sentiment & Einfluss</strong></summary>
<p>
  <img src="docs/images/screenshot-sentiment-1.png" alt="Plattform-Verteilung & Aktivität" width="800">
  <img src="docs/images/screenshot-sentiment-2.png" alt="Sentiment-Verlauf" width="800">
  <img src="docs/images/screenshot-influence-1.png" alt="Einfluss-Strömung" width="800">
</p>
</details>

<details>
<summary><strong>Analyse-Report</strong></summary>
<p>
  <img src="docs/images/screenshot-report.png" alt="Report Übersicht" width="800">
  <img src="docs/images/screenshot-report-2.png" alt="Report Details" width="800">
  <img src="docs/images/screenshot-report-3.png" alt="Report Risiken" width="800">
</p>
</details>

---

<h2 id="features">Features</h2>

<table>
  <tr>
    <td width="50%">
      <h3>Virtuelle Marktforschung</h3>
      <p>10 bis 500 KI-Personas mit Big-Five-Persönlichkeit, demographischem Profil und individueller Meinung. Verteilt nach Rogers Diffusion: Innovatoren, Early Adopters, Skeptiker, Traditionalisten.</p>
    </td>
    <td width="50%">
      <h3>Deep Mode: Web-Recherche</h3>
      <p>Vor der Simulation recherchiert Agora automatisch die aktuelle Marktlage — Wirtschaft, Branchentrends, Zielgruppen-Stimmung. Personas leben in der Realität von <em>heute</em>, nicht in generischem LLM-Wissen.</p>
    </td>
  </tr>
  <tr>
    <td>
      <h3>Anti-Echo-Chamber</h3>
      <p>Bounded Confidence, Conviction Strength, Opposing-View-Injection und automatische Contrarian-Posts verhindern unrealistische Massenkonversion. Skeptiker bleiben skeptisch — wenn sie es sein sollten.</p>
    </td>
    <td>
      <h3>Konfidenz-Bewertung</h3>
      <p>Jede Erkenntnis im Report wird mit [HOHE], [MITTLERE] oder [NIEDRIGE KONFIDENZ] bewertet. Der Report sagt ehrlich, was belastbar ist und was validiert werden muss.</p>
    </td>
  </tr>
  <tr>
    <td>
      <h3>Multi-Provider</h3>
      <p>Anthropic Claude, OpenAI GPT-5, Ollama (lokal) — frei wählbar pro Simulationsphase. Provider-Capabilities werden dynamisch abgefragt, nicht unterstützte Parameter automatisch ausgeblendet.</p>
    </td>
    <td>
      <h3>Multi-Run & Stress-Tests</h3>
      <p>Gleiche Simulation 3-5x laufen lassen und Varianz messen. Sensitivity-Tests mit verändertem Skeptiker-Anteil. Remove-and-Rerun: einflussreichste Akteure entfernen und prüfen ob das Ergebnis stabil bleibt.</p>
    </td>
  </tr>
</table>

---

<h2 id="so-funktioniert-es">So funktioniert es</h2>

```
Simulation erstellen          Produkt, Markt, Branche beschreiben
        |
   [Deep Mode?] ----ja----> Web-Recherche (DuckDuckGo + LLM-Synthese)
        |                         |
        |                   MarketContext prüfen & bestätigen
        |                         |
        v                         v
  Persona-Generierung        mit aktuellem Marktkontext
  (Hybrid: Skelette               |
   + Enrichment)                   |
        |                          |
        v                          v
  Tick-Schleife (15-30 simulierte Tage)
  Pro Tag: Personas posten, kommentieren,
  reagieren, ändern Meinung
        |
        v
  Automatischer Analyse-Report
  Sentiment, Wendepunkte, Zielgruppen,
  Influence-Netzwerk, Konfidenz-Levels
```

---

<h2 id="quickstart">Quickstart</h2>

### Voraussetzungen

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose
- Einen [Anthropic API Key](https://console.anthropic.com/) (oder OpenAI)

### Setup

```bash
# 1. Repository klonen
git clone https://github.com/dein-user/agora.git && cd agora

# 2. Environment konfigurieren
cp .env.example .env
# .env öffnen und ANTHROPIC_API_KEY eintragen

# 3. Starten
docker compose up --build -d

# 4. Warten auf "Application startup complete."
docker compose logs -f app
```

### Ersten API-Key erstellen

<details>
<summary><strong>Linux / macOS / Git Bash</strong></summary>

```bash
curl -X POST http://localhost:8000/admin/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "Mein Key"}' \
  -H "X-Admin-Key: change-me-in-production"
```

</details>

<details>
<summary><strong>Windows PowerShell</strong></summary>

```powershell
Invoke-RestMethod -Uri http://localhost:8000/admin/keys -Method POST `
  -ContentType "application/json" `
  -Headers @{"X-Admin-Key"="change-me-in-production"} `
  -Body '{"name":"Mein Key"}'
```

</details>

### Loslegen

1. Öffne **http://localhost:8000** im Browser
2. Login mit dem API-Key
3. Erste Simulation erstellen — fertig!

---

## Tech Stack

| Schicht | Technologie |
|---------|-------------|
| **Frontend** | Angular 21, TailwindCSS 4, ECharts, Sigma.js |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Pydantic |
| **Datenbank** | PostgreSQL 16, Alembic (Migrationen) |
| **LLM** | Anthropic Claude 4.x, OpenAI GPT-5, Ollama (lokal) |
| **Recherche** | DuckDuckGo Search (kein API-Key nötig) |
| **Infrastruktur** | Docker (Multi-Stage Build), SSE (Live-Updates) |

---

<h2 id="api">API-Dokumentation</h2>

Interaktive Docs: **http://localhost:8000/docs** (Swagger UI)

<details>
<summary><strong>Wichtigste Endpoints</strong></summary>

| Endpoint | Beschreibung |
|----------|-------------|
| `POST /simulations/` | Simulation erstellen |
| `POST /simulations/{id}/run` | Simulation starten |
| `GET /simulations/{id}/stream` | Live-Fortschritt (SSE) |
| `GET /simulations/{id}/market-context` | Web-Recherche-Ergebnis |
| `POST /simulations/{id}/research/approve` | Recherche bestätigen |
| `POST /simulations/{id}/multi-run` | Multi-Run starten |
| `POST /analysis/{id}/generate` | Report generieren |
| `GET /analysis/{id}` | Report abrufen |
| `POST /personas/{id}/chat` | Mit Persona chatten |
| `GET /providers/capabilities` | Provider-Fähigkeiten |

</details>

---

<h2 id="konfiguration">Konfiguration</h2>

Alle Einstellungen über Umgebungsvariablen (`.env`):

| Variable | Pflicht | Standard | Beschreibung |
|----------|:-------:|----------|-------------|
| `ANTHROPIC_API_KEY` | **Ja** | — | Claude API Key |
| `OPENAI_API_KEY` | Nein | — | OpenAI als alternativer Provider |
| `ADMIN_MASTER_KEY` | **Ja** | `change-me-in-production` | Für API-Key-Erstellung |
| `DATABASE_URL` | Nein | *von Docker gesetzt* | PostgreSQL Connection |
| `CORS_ORIGINS` | Nein | `["*"]` | Erlaubte Origins |
| `MAX_CONCURRENT_SIMULATIONS` | Nein | `3` | Parallele Simulationen |

---

## Was Agora NICHT ist

- **Keine echte Marktforschung** — Agora generiert Hypothesen, keine Beweise
- **Keine Kaufprognosen** — Personas simulieren Meinungsdynamiken, kein Kaufverhalten
- **Kein Ersatz für echte Kunden** — Agora ist ein Pre-Screening-Tool
- **Quantitative Claims von Personas sind keine echten Daten**

---

## Lizenz

Proprietär. Alle Rechte vorbehalten.

---

<p align="center">
  <sub>Gebaut mit Claude, GPT und sehr viel Kaffee. DSGVO-nativ. Europäisch.</sub>
</p>
