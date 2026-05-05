# Analyse-Report

## Zusammenfassung

### Ausgangslage
Diese Auswertung basiert auf einer Simulation (20 ingame‑Tage, 200 Personas; 96 company, 67 expert, 15 media, 15 research_institute, 5 private_person, 2 influencer; 240 Beiträge, 849 Einfluss‑Events). Produktfokus: „Agora“ – ein SaaS‑Tool, das klassische Marktforschung partiell durch KI‑Personas ersetzt/ergänzt (200 simulierte Persönlichkeiten debattieren in 30 Minuten; Preis: 99 € je Run). Ziele der Analyse: (1) Wahrnehmung durch klassische Marktforscher (Bedrohung vs. ergänzendes Vor‑Screening), (2) Zahlungsbereitschaft von Pre‑Seed‑Gründern (99 € vor echten Interviews), (3) Reaktionslage (Begeisterung/Ablehnung/Skepsis) je Zielgruppe im DACH‑B2B‑Kontext.

Wichtige Kontextsignale: 40% der Akteure sind als Skeptiker markiert. Der Diskurs ist B2B/institutionell geprägt: Compliance, DSGVO, Auditierbarkeit, Repräsentativität, Bias‑Kontrolle (u. a. CH‑Sprachen) sowie Reproduzierbarkeit dominieren. Mehrfach gefordert: präregistrierte Prüfprotokolle, Persona‑Seeds, Prompt‑Versionen, Sampling‑/Kalibrierungs‑Logs, Ground‑Truth‑Vergleiche gegen Panels/Verhaltensdaten. 

### Kernerkenntnisse
1) **Agora wird von Fachcommunity und Instituten klar als Vor‑Screening/Pre‑Filter eingestuft – nicht als Ersatz klassischer Forschung.** Zahlreiche Stimmen (z. B. Reto Schmid, Prof. Dr. Natascha Kiener, Prof. Dr. Viola Rüggeberg, Dr. Heike Grabner) verwerfen „Ersetzen“-Claims; positivere Stimmen (z. B. Gregor Höller, Selina Obrist, Marco Sutter) betonen Effizienz im Hypothesen‑Triage. Aus der Expert:innen‑/Institutskohorte deuten >75% der Beiträge auf „Ergänzung, nicht Ersatz“. [HOHE KONFIDENZ]
2) **Kauf-/Pilotbereitschaft ist an harte Guardrails geknüpft (Präregistrat, Audit‑Trail, Ground‑Truth‑Validierung, DSGVO, Haftung).** Typische Listenforderungen: Nadja Hämmerli (CH‑Bias‑Checks, Audit‑Trail, KPI‑Verknüpfung), Tobias Hollenstein (Pilot unter klaren Vorbedingungen), Reto Schmid (revisionssichere Nachweise). Ohne Guardrails: überwiegend Ablehnung. [HOHE KONFIDENZ]
3) **Preiswiderstand ist gering – der Engpass ist Validität, nicht 99 €.** Die Meinungsdimension „price_fairness“ liegt im Mittel bei +0,06 (48% positiv); direkte Preisdebatten fehlen fast vollständig. Mehrere potenzielle Käufer akzeptieren 30‑Minuten‑Runs als „Stage‑0‑Pretest“, sofern validiert (z. B. Philipp Mittermeier, Leonie Gerster, Marco Sutter). [MITTLERE KONFIDENZ]
4) **Narrativ „Konfidenz in 30 Minuten ersetzt zwei Wochen UXR“ erzeugt Gegenwind und mobilisiert Gatekeeper.** Posts von Theresa Aigner, die Ersatzbehauptungen andeuten, triggern methodische Gegenreaktionen (z. B. Prof. Reto Meier, Marlene Pospisil, Katrin Wieser). Transparenzangebote (Präregistrat, Artefakte) mindern den Widerstand, ersetzen ihn aber nicht. [HOHE KONFIDENZ]
5) **Klar segmentierbare Reaktionsmuster:** 
   - Experten/Institute: überwiegend skeptisch/ablehnend, verlangen strikte Ex‑Post‑Validierung. 
   - Unternehmen/Gründer: geteilt – „pilot‑bereit unter Guardrails“ vs. „skeptisch bis Ablehnung“.
   - Medien: kritisch‑prüfend, treiben Transparenzagenda. 
   - Influencer/Praktiker (z. B. Gregor Höller): pro‑Tempo, aber „Validation first“. [HOHE KONFIDENZ]

### Risiken & Chancen
Risiken:
- Reputationsrisiko durch Überversprechen („ersetzt zwei Wochen UXR“) – triggert „Scheinpräzisions“-Vorwurf (u. a. Dr. Selma Kogler, Laura Pichler). [HOHE KONFIDENZ]
- Compliance/DSGVO-/Haftungsanforderungen als Deal‑Stopper in Enterprise‑Beschaffung (Reto Schmid; Anja Kofler). [HOHE KONFIDENZ]
- Schweiz‑spezifische Repräsentativität/Bias (Nadja Hämmerli) – Blocker in DACH‑Rollouts. [MITTLERE KONFIDENZ]
- Gatekeeper‑Skepsis (Institute/Verbände) bremst Akzeptanz, solange keine unabhängige Feldvalidierung vorliegt. [HOHE KONFIDENZ]

Chancen:
- „Stage‑0“-Beschleuniger: 30‑Minuten‑Debatten liefern Top‑Einwände/Segmentkontroversen (Selina Obrist: „Top‑3 Einwände je Segment in 30 Minuten“). [HOHE KONFIDENZ]
- Kosten-/Zeitersparnis (Marco Sutter; Leonie Gerster will 2 Markenpiloten) – besonders attraktiv für Pre‑Seed/PM‑Teams. [MITTLERE KONFIDENZ]
- Partnering mit Methodik‑Gatekeepern via präregistrierte, reproduzierbare PoCs (stark geforderter Standard). [HOHE KONFIDENZ]

### Strategische Empfehlungen
- Positionierung schärfen: **„Pre‑Screening für Hypothesenpriorisierung“ statt „Ersatz“.** Verbindliche Distanzierung von Ersatz‑Claims. [HOHE KONFIDENZ]
- **Standardisiertes Prüfprotokoll** publizieren (Präregistrat, Persona‑Seeds, Prompt‑Historie, Sampling‑/Kalibrierungs‑Logs, Bias‑Bericht nach Sprachregionen, Explainability‑Artefakte, Fehlermodell). [HOHE KONFIDENZ]
- **DACH‑Referenz‑PoCs** mit unabhängigen Mitprüfern (Media/Institut) und harten Out‑of‑Sample‑Vergleichen (Panel/A/B). [HOHE KONFIDENZ]
- **DSGVO‑/Haftungs‑Paket** („Trust Add‑On“): On‑Prem/BYOM‑Option, Datenherkunft, Audit‑Trail, Eskalationspfade. [HOHE KONFIDENZ]
- **Preis-/PLG‑Motion beibehalten (99 €)**, aber an „Guardrailed‑Templates“ koppeln (CH‑Bias‑Template, B2B‑Kaufpfad‑Template). [MITTLERE KONFIDENZ]
- **Multiplikatoren gezielt einbinden** (Gregor Höller, Tobias Hollenstein, Leonie Gerster) als Brückenakteure in Co‑Piloten. [MITTLERE KONFIDENZ]

Hinweis: Dies ist eine Simulation, keine echte Marktforschung. Prozentwerte, Zitate und Schlussfolgerungen sind Artefakte der simulierten Diskurslandschaft und müssen real validiert werden.


## Sentiment-Verlauf

### Sentiment-Verlauf (20 Tage)
- Anfangsphase (Tag 1–3): Gemischte bis kritische Grundstimmung. Frühe Begeisterung einzelner Praktiker (z. B. Theresa Aigner; Gregor Höller: „brutal effizient“), aber starker methodischer Gegenwind (Maren Yıldırım, Reto Schmid). Medien/Institute fordern von Beginn an Transparenz (Audit‑Trail, Trainingsdaten, Ground‑Truth‑Validierung).
- Mittelteil (Tag 4–12): Zuspitzung der Skepsis durch „Ersatz“-Narrativ. Theresas Tag‑4‑Post („ersetzt mir zwei Wochen UXR“) löst spürbare Gegenreaktionen (Katrin Schober, Laura Pichler). Gegensteuerung durch Transparenz‑Offerten (Präregistrat, Artefakte) dämpft Tonalität punktuell (Tag 9–11), ohne Stimmungswende. Crowd‑Layer meldet teils positive Ausschläge (Ticks 14–16), im Fachdiskurs bleibt die Linie: „Tempo ja, Entscheidungsevidenz nur mit Validierung“.
- Endphase (Tag 13–20): Stabil hohe methodische Anforderungen, langsames Anwachsen „pilot‑bereit unter Guardrails“. Tag 15: Sibel Yildirim („No Paint, Only Plumbing“) verstärkt Vertrauen bei praxisorientierten Stakeholdern; Medien/Institute verharren auf „Validität vor Geschwindigkeit“.

Konkrete Umschwünge:
- Tag 4: Negativer Kipppunkt durch Ersatz‑Behauptung – multiple Ablehnungen („Scheinpräzision“). 
- Tag 9–11: Leichte Entspannung durch Angebot zur Artefakt‑Freigabe/Präregistrat; mehr Bereitschaft zu PoC‑Co‑Designs.
- Tag 15: Vertrauensimpuls aus Praxis („Artefakte, kein Lack“), dennoch keine breite Akzeptanz ohne externe Validierung.


## Sentiment nach Akteurs-Typ

Typ | Anzahl | Sentiment | Kernhaltung
--- | --- | --- | ---
Privatperson | 5 | überwiegend pragmatisch‑offen | Nutzen als Hypothesen‑Turbo, Anti‑Hype (z. B. Sevda Karakus)
Firma | 96 | gemischt | Pilot‑Bereitschaft unter Guardrails; Enterprise verlangt DSGVO/Haftung
Institut | 15 | eher skeptisch | Validität vor Geschwindigkeit, Replikationsrechte
Behörde | 0 | – | –
Medium | 15 | kritisch‑prüfend | Transparenz, Anti‑„Scheinpräzision“ (Marlene Pospisil)
Influencer | 2 | positiv‑pragmatisch | Tempo + A/B‑Tests (Gregor Höller); Evangelismus mit Transparenzangebot (Theresa Aigner)
Experte | 67 | überwiegend skeptisch | Ground‑Truth, Fehlermodelle, Präregistrat
Kollektiv | – | – | –
Validierer | – | – | –

Schlüssel‑Zitate:
- „30‑Minuten‑Run ist ein schneller Hypothesenscan, kein inferenzielles Urteil.“ (Prof. Reto Meier)
- „Top‑3 Einwände pro Segment in 30 Minuten – verhindert teure Tests.“ (Selina Obrist)


## Wendepunkte

1) **Tag 2 — Institutionelle Skepsis formiert sich**: Reto Schmid (Feedbook) erklärt „200 KI‑Personas ohne auditierbaren Stichprobenplan“ für nicht compliance‑fähig. Wirkung: methodische Checklisten werden Branchenstandard im Thread; zahlreiche Experten (Prof. Natascha Kiener) flankieren.
2) **Tag 4 — „Ersatz“-Narrativ triggert Backlash**: Theresa Aigner bekräftigt Tempo‑Vorteil; Replik von Katrin Schober/Laura Pichler: „Scheinpräzision ohne Kalibrierung“. Ergebnis: deutlicher Stimmungsdämpfer, Fixierung auf Validität/Präregistrierung.
3) **Tag 9 — Transparenzangebot öffnet Prüfpfad**: Theresa bietet Artefakte + Präregistrat an; hoher Impact (64 Reaktionen). Patrizia Koller: Mitwirkung am methodischen Review bei präregistriertem Plan.
4) **Tag 11–13 — PoC‑Koalitionen**: Gregor Höller schlägt duale Varianten mit echten Conversion‑Metriken vor; Sibel Yildirim bestätigt Artefakte. Ergebnis: „pilot‑bereit unter Guardrails“ gewinnt leicht.
5) **Tag 15 — „No Paint, Only Plumbing“** (Sibel Yildirim): Technisch‑methodische Zusage (Seeds, RNG, Prompts, Kalibrierungs‑Code) erhöht Pragmatismus bei Pilot‑Interessenten (z. B. Severin Patek anerkennt Richtung, bleibt prüfend).


## Kritikpunkte

- **Scheinpräzision/Ersetzen‑Claim**: Medien/Experten (Marlene Pospisil, Dr. Selma Kogler, Laura Pichler) kritisieren „Konfidenz in 30 Minuten“ ohne Ground‑Truth‑Kalibrierung als trügerisch; ca. 80–90% der Expert:innen/Institute teilen dies. [HOHE KONFIDENZ]
- **Fehlende Auditierbarkeit (Persona‑Seeds/Prompts/Logs)**: Nadja Hämmerli, Anja Wüstner, Reto Schmid fordern maschinenlesbare Artefakte; >70% der Fachbeiträge verlangen vollständige Reproduzierbarkeit. [HOHE KONFIDENZ]
- **Trainingsdaten‑/Bias‑Transparenz (insb. CH‑Sprachen)**: wiederholte Forderung (Nadja Hämmerli, Severin Aeschlimann); Anteil der Beiträge mit Bias‑Fokus: ~35–45% der kritischen Stimmen. [MITTLERE KONFIDENZ]
- **Fehlendes Fehlermodell/Konfidenzdefinition**: Dr. Markus Wawrzyniak u. a. verlangen Unsicherheitsmaße, posterior predictive checks; >50% der Fachbeiträge referenzieren Kalibrierung/Test‑Retest. [MITTLERE KONFIDENZ]
- **Compliance/DSGVO/Haftung unklar**: Reto Schmid, Anja Kofler; ca. 40–50% der Enterprise‑/Konkurrenz‑Posts benennen dies explizit. [MITTLERE KONFIDENZ]


## Chancen

- **Stage‑0‑Pretests zur Hypothesenpriorisierung**: „In 30 Minuten Top‑3 konträre Einwände je Segment“ (Selina Obrist, Feedbook Tag 9/12/15/19). Potenzial: Verkürzung von Sechs‑Wochen‑Pretests auf 1–2 Sprints. [MITTLERE KONFIDENZ]
- **Pilot‑Designs mit Messdisziplin**: Leonie Gerster (Tag 14): „Keine These ohne Zahl. Keine Zahl ohne Kontrollbedingung.“ Potenzial: belastbare Referenz‑Cases für DACH. [HOHE KONFIDENZ]
- **Brückenakteure als Multiplikatoren**: Gregor Höller (mehrfach): „A/B‑Tests, keine Dogmen“. Potenzial: Community‑getriebene Standardisierung (Präregistrat‑Templates). [MITTLERE KONFIDENZ]
- **PLG‑Motion (99 €) + Templates**: Niedrige Einstiegshürde, insbesondere für Pre‑Seed/PM‑Teams; Price Fairness positiver als andere Dimensionen (Ø +0,06). [MITTLERE KONFIDENZ]


## Zielgruppen

### Unternehmen (Produkt/Marketing/PM)
- Größe: 96 (48% der Simulation). Haltung: geteilt; „pilot‑bereit unter Guardrails“ vs. skeptisch. Schlüsselakteure: Marco Sutter (Pilot), Leonie Gerster (2 Markenpiloten), Tobias Hollenstein (Pilotkriterien), Korbinian Althammer (DACH‑Messaging). Empfehlung: Guardrail‑Pakete (Präregistrat, Logs, DSGVO/Haftung), Success‑Plans mit A/B‑KPIs.

### Experten (Beratung/Methodik)
- Größe: 67 (33,5%). Haltung: überwiegend skeptisch/ablehnend. Schlüsselakteure: Prof. Reto Meier, Dr. Markus Wawrzyniak, Prof. N. Kiener, Prof. V. Rüggeberg. Empfehlung: Co‑Design von Prüfprotokollen, offene Artefakte (Seeds/Prompts/Logs), gemeinsame Publikation von Kalibrierungsbefunden.

### Forschungsinstitute
- Größe: 15 (7,5%). Haltung: methodisch strikt, Gatekeeper‑Rolle. Schlüssel: Anke Vogt, Dr. Ulrike Baumgartner. Empfehlung: Unabhängige Validierungspfade (Holdout‑Sets, Panel‑Vergleiche), MoUs für Replikationsrechte.

### Medien (Fachdiskurs)
- Größe: 15 (7,5%). Haltung: kritisch‑prüfend, Transparenztreiber. Schlüssel: Marlene Pospisil, Sina Gmür, Katharina Pichler. Empfehlung: „Open Methods“-Seite, Presse‑Sandbox mit Live‑Artefakten.

### Private Personen/Gründer (Pre‑Seed)
- Größe: 5 (2,5%). Haltung: pragmatisch, kosten‑/zeitgetrieben, „Hype‑Allergie“. Schlüssel: Sevda Karakus. Empfehlung: Self‑Serve‑PoCs (99 €) mit klaren Kill‑Kriterien, Video‑Walkthrough „Vom Run zur Interview‑Leitfadenableitung“.

### Influencer/Praktiker
- Größe: 2 (1%). Haltung: pro Tempo, aber streng experimentgetrieben. Schlüssel: Theresa Aigner (Evangelistin), Gregor Höller (Evangelist/Brücke). Empfehlung: Co‑hostete Pilotstudien, Public‑Präregistrate.


## Ueberraschungen

1) **Preis ist kein Streitpunkt – Validität ist es.** Kaum offene Preisdebatten; Widerstand zielt fast ausschließlich auf Auditierbarkeit/Validierung.
2) **Schweizer Mehrsprachigkeit als prominenter Bias‑Treiber.** CH‑Sprachen tauchen wiederholt als Must‑have in der Due Diligence auf (Nadja Hämmerli).
3) **Crowd‑Layer meldet mehrfach positive Sentiment‑Ticks, während Fachdiskurs skeptisch bleibt.** Möglicher Plattform‑/Publikums‑Bias.
4) **Influencer agieren als methodische Brücken, nicht als Hype‑Verstärker.** Gregor Höller fordert A/B‑Tests statt Dogmen.
5) **„Ersatz“-Narrativ schadet mehr als es nützt.** Jede Zuspitzung in diese Richtung generiert spürbaren Backlash und verschiebt Kapazität auf Abwehr/Prüfaufwand.


## Influence-Netzwerk

### Top‑Influencer (Impact‑Indikatoren)
- Theresa Aigner (Threadit): mehrfach zweistellige Reaktionen; Tag 9‑Post mit 64 Reaktionen – zentraler Katalysator für Transparenzdebatte.
- Prof. Reto Meier (Threadit, Tag 5): 33 Reaktionen – methodischer Anker, der Prüfstandards verdichtet.
- Sibel Yildirim (Feedbook, Tag 15): 18 Reaktionen – „No Paint, Only Plumbing“ als Praxis‑Signal.
- Marlene Pospisil (Threadit): hohe Sichtbarkeit, wiederkehrende Ablehnungen („synthetische Einigkeit“), Gatekeeper‑Funktion im Mediendiskurs.

### Überzeugungsketten (Beispiele)
- Theresa Aigner → Patrizia Koller → Co‑Review‑Bereitschaft (Tag 9). 
- Gregor Höller → Pilot‑Design‑Vorschläge → Zustimmung/Anschluss durch weitere Praktiker (z. B. Lukas Bernhard).
- Reto Schmid → methodischer Mindeststandard → breite Referenzierung (Kiener, Rüggeberg, Aeschlimann).

### Einflussreichste Beiträge (Zitate)
- Theresa Aigner (Tag 9): „Artefakte + Präregistrat“ – öffnet PoC‑Pfad („Ich beteilige mich am PoC…“ — Patrizia Koller).
- Prof. Reto Meier (Tag 5): „30‑Minuten‑Run = Hypothesenscan, keine Inferenz“ – verdichtet Prüfanforderungen.
- Sibel Yildirim (Tag 15): „No Paint, Only Plumbing“ – fordert komplette Roh‑Artefakte (Seeds, RNG, Prompt‑History, Kalibrierungs‑Code).


## Plattform-Dynamik

### Tonalität und Aktivität
- Threadit: praxisnah, dialogisch, PoC‑/Pilotdiskussionen („wir präregistrieren…“, „2 Markenpiloten“). Influencer‑ und Company‑Lastigkeit; mehr konstruktive Guardrail‑Vorschläge.
- Feedbook: formelle Stellungnahmen, methodische/Compliance‑Bedenken (Reto Schmid, Anke Vogt), härtere Ablehnungen. Höherer Anteil Forschungsinstitute/Medien.

### Plattformspezifische Themen
- Threadit: Präregistrate, A/B‑Designs, Success‑Metriken, Artefakt‑Freigaben.
- Feedbook: Repräsentativität, DSGVO/Haftung, Scheinpräzision, Validierer‑Anforderungen.


## Plattform-Vergleich

### Threadit vs. Feedbook (v1.1)
- Engagement: Threadit höher dialogisch (Kommentare, Repliken, Pilotdesigns); Feedbook formeller, mit Positionspapieren.
- Tonalität: Threadit tendenziell pragmatischer/positiver, Feedbook skeptischer/prüfender.
- Dominante Akteurs‑Typen: Threadit – Firmen/Influencer; Feedbook – Institute/Medien/Competitors.
- Plattformspezifische Themen: Threadit (Präregistrat, A/B‑Metriken), Feedbook (Compliance/DSGVO, Repräsentativität, Haftung).


## Netzwerk-Evolution

- **Community‑Cluster:** (a) Evangelisten/Praktiker (Tempo+Validation), (b) Methodik‑/Instituts‑Gatekeeper (Validität vor Tempo), (c) Unternehmens‑„Swing“-Gruppe (pilot‑bereit unter Guardrails). 
- **Brückenakteure:** Gregor Höller (verbindet (a) und (c)), Patrizia Koller (öffnet Review‑Pfad in (b)). 
- **Echokammern:** Feedbook‑Strang mit repetitiven Ablehnungen; Threadit mit praxisnahen, aber teils evidenzarmen Zuspruchshappen. 
- **Konvergenzpunkte:** Präregistrat + offene Artefakte als gemeinsamer Nenner für Dialogfortsetzung.


## Validierer-Status

Keine Validierer in dieser Simulation.

## Trigger-Wirkung

Keine Trigger-Events in dieser Simulation.

## Stagnation

Leichte Aktivitätsdellen (z. B. Tag 12, 20) ohne erkennbare Stagnation. Auto‑Reaktivierung nicht protokolliert. Insgesamt kontinuierlicher Diskursfluss.

## Schluessel-Akteure

- **Top‑3 Brückenakteure:** Gregor Höller (Influencer; verbindet Praxis und Methodik), Patrizia Koller (Expertin; öffnet Review‑Pfad), Lukas Bernhard (Media/Observer; moderat methodisch, offen für PoC‑Design).
- **Top‑5 Multiplikatoren:** Theresa Aigner (Evangelistin; 64 Reaktionen an Tag 9), Prof. Reto Meier (33 Reaktionen, methodischer Referenzpost), Sibel Yildirim (Praxis‑Signal; 18 Reaktionen), Marlene Pospisil (wiederkehrende, reichweitenstarke Kritik), Reto Schmid (Compliance‑Leitplanken).
- **Meinungs‑Gatekeeper:** Prof. Natascha Kiener, Prof. Viola Rüggeberg, Dr. Heike Grabner – setzen methodische Mindeststandards (Kalibrierung, Bias‑Audit, Replikation).


## Konfidenz-Bewertung

### Hohe Konfidenz
- „Ergänzung, nicht Ersatz“ ist Mehrheitskonsens in Experten/Instituten (umfangreich belegt durch zahlreiche Posts; mehrere Tage, verschiedene Akteure). 
- Guardrails (Präregistrat, Audit‑Trail, Ground‑Truth‑Validierung) sind Voraussetzung für Pilots. 
- Ersatz‑Rhetorik erzeugt Backlash/„Scheinpräzision“-Vorwürfe.

### Mittlere Konfidenz
- 99 € werden akzeptiert; Engpass ist Validierung, nicht Preis (indirekte Evidenz: positive price_fairness; wenige Preisdebatten). 
- Schweiz‑Bias (CH‑Sprachen) als Adoptionshürde (wiederkehrend in Kommentaren; aber unquantifiziert).
- Wachstumspotenzial über „Stage‑0“-Einsatz in PM/Pre‑Seed‑Teams (viel Zuspruch, aber ohne harte Nutzungsdaten).

### Niedrige Konfidenz
- Exakte Größenordnung der Zahlungsbereitschaft Pre‑Seed‑Gründer (wenige direkte Preisaussagen). 
- Crowd‑Layer‑Sentiment als Abbild der Fachstimmung (plattformspezifische/algorithmische Artefakte möglich). 
- Geschätzte Pilotquote in Enterprises (stark abhängig von Einzelchampions und Compliance‑Pfaden).


## Methodische Grenzen

- Simulation, keine echte Marktforschung: Persona‑Verhalten ist LLM‑generiert; Aussagen sind Narrative, nicht beobachtetes Kaufverhalten.
- Quantitative Claims aus Posts („70% ersetzen“ etc.) sind Persona‑Behauptungen, keine Marktdaten.
- Echokammer‑Effekte: schnelle Konsensbildung einzelner Stränge möglich; Plattform‑Bias (Threadit vs. Feedbook) verfälscht Stimmungen.
- Die Simulation testet Narrative und Reibungspunkte, nicht reale Zahlungsbereitschaft, ROI oder Akzeptanz in Gremien.
- Vor Real‑Entscheidungen zu validieren: (1) Feld‑PoCs mit präregistrierten Plänen und OOS‑Validierung, (2) DSGVO/Haftungs‑Audit, (3) Bias‑/CH‑Sprachtests, (4) Zahlungsbereitschaftstest (Pricing‑Page‑A/B; 99 € vs. Bundles), (5) Replikation durch unabhängige Institute.


