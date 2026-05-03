# Fix: Kosten- und Zeitschätzung komplett überarbeiten

## Problem
- Kostenschätzung: 8€ angezeigt, 20€+ verbraucht (Faktor 2.5x daneben)
- Zeitschätzung: 20 Min angezeigt, 3-4 Std real (Faktor 10-12x daneben)

## Ursachen

### Kosten
1. Token-Schätzungen stammen aus der alten Batch-Architektur (1 Call = 15 Personas)
2. Hybrid-Generierung macht VIEL mehr Calls: 67 Skelett-Batches + 200 Enrichment-Calls
3. Deep Mode Web-Recherche (Query-Gen + Suche + Synthese) wird nicht eingerechnet
4. Report-Generierung mit MarketContext ist teurer (längerer Prompt)
5. Enrichment nutzt Smart-Tier statt Fast-Tier — 10x teurer als kalkuliert

### Zeit
1. Parallelisierung überschätzt: "180 Persona-Aktionen pro Minute" stimmt nicht bei GPT-5
2. Persona-Generierung nicht eingerechnet (Hybrid = 67 Skelett + 200 Enrichment Calls)
3. Deep Mode Recherche nicht eingerechnet (~5 Min)
4. Report-Generierung nicht eingerechnet (~2-5 Min)
5. GPT-5 ist deutlich langsamer als GPT-5-mini/Haiku

## Status
- [x] Token-Schätzungen aktualisieren (Backend _TOKEN_ESTIMATES)
- [x] Hybrid-Generierung in Kalkulation einbeziehen (2500/1500 statt 800/350)
- [x] Deep Mode Aufschlag (5000/3000 für Recherche)
- [x] Zeitschätzung komplett neu berechnen (Hybrid-Gen + 6s/Call + 2 Phasen/Tick)
- [x] Frontend-Anzeige aktualisieren (estimatedCost + estimatedMinutes)
- [x] Warnungsschwelle auf 30 Min gesenkt
