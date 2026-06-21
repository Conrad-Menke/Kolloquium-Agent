# Kolloquium-Agent

Ein opencode-Skill, der einen Corpus an PDFs in einen **NRW-Kolloquiums-Coach**
verwandelt. Gebaut für die Zweite Staatsprüfung (`Vorbereitungsdienst` /
`Referendariat`).

Der Skill läuft in drei Modi:

- **Modus A — Simulation**: ein dynamisches Prüfungsgespräch im echten NRW-Format.
  Du eröffnest mit einem selbst gewählten *Kurzvortrag*; der Agent greift die
  "losen Enden" auf, die du liegen lässt, und entwickelt ein fließendes Gespräch
  über die Handlungsfelder, in dem empirische Fundierung mit eigener Erfahrung
  verwoben wird.
- **Modus B — Karteikarten**: erzeugt Lernkarten. Jede Karte hat eine fiktive
  Prüfungsfrage, 3–5 Antwort-Schlagworte und die exakte Quellenstelle aus den
  PDFs.
- **Modus C — Aufbau**: der Agent wechselt die Rolle vom Prüfer zum Mentor
  und erklärt dir interaktiv, wie dieser Skill funktioniert — von der
  RAG-Grundidee bis zur konkreten Datei. Du fragst, der Agent antwortet
  grounded in den tatsächlichen Dateien dieses Repos statt aus dem Gedächtnis
  zu zitieren.

Jede Frage und jede Karte ist **in abgerufenen Textstellen verankert**. Wenn
der Corpus eine Frage nicht hergibt, sagt der Agent das auch, statt etwas zu
erfinden. Grounding wird dadurch erzwungen, dass der Agent **nur** auf die
Passagen Zugriff hat, die ein Retrieval-Schritt zurückliefert.

## Layout

```
.
├── AGENTS.md                       # Agent-Anweisungen (Repo-Ebene)
├── opencode.json                   # opencode-Konfiguration + Berechtigungsregeln
├── .opencode/
│   └── skills/kolloquium -> ../../skills/kolloquium   # Discovery-Symlink (s.u.)
├── skills/
│   └── kolloquium/
│       ├── SKILL.md                # Der Prüfer-Skill (Persona + Regeln)
│       ├── scripts/
│       │   ├── index_corpus.py     # PDF/DOCX parsen + chunken + embedden → Chroma
│       │   ├── retrieve.py         # Query → JSON-Passagen
│       │   └── requirements.txt
│       ├── data/                   # PDFs/DOCX landen hier (gitignored)
│       └── index/                  # Chroma-DB (gitignored)
```

## Quickstart

Von null bis zur ersten Kolloquiumssession in fünf Schritten.

### 1. opencode installieren

Ein Befehl lädt die neueste Version herunter und installiert sie:

```bash
curl -fsSL https://opencode.ai/install | bash
```

Danach kannst du `opencode` im Terminal aufrufen. Auf macOS alternativ
`brew install opencode`, auf Arch `paru -S opencode`. Details siehe
<https://opencode.ai/docs>.

### 2. Repo klonen

```bash
git clone https://github.com/Conrad-Menke/Kolloqium-Agent.git
cd Kolloqium-Agent
```

### 3. Skill in opencode bekannt machen

opencode entdeckt Skills nur unter festen Pfaden (siehe
<https://opencode.ai/docs/skills/>): `.opencode/skills/<name>/SKILL.md`
(projektlokal) oder `~/.config/opencode/skills/<name>/SKILL.md` (global).
Ein nackter `skills/`-Ordner am Repo-Root wird *nicht* gefunden — darum
kümmert sich dieser Schritt.

Dieses Repo legt den projektlokalen Pfad als Symlink an, damit das
Original unter `skills/kolloquium/` liegen bleiben kann:

```bash
mkdir -p .opencode/skills
ln -s ../../skills/kolloquium .opencode/skills/kolloquium
```

Wer den Skill projektübergreifend nutzen will, zusätzlich global verlinken:

```bash
ln -s "$(pwd)/skills/kolloquium" \
      "$HOME/.config/opencode/skills/kolloquium"
```

### 4. Erste Session starten

```bash
opencode
```

Im Chat den Skill mit einer Trigger-Phrase aktivieren, z. B.:

> "Führe ein Kolloquium mit mir."

### 5. Modus wählen

Der Skill läuft dann eine **Aktivierungsrunde**:

1. Fragt nach dem Ordner oder den PDF-/DOCX-Dateien (Ordner werden rekursiv
   durchsucht).
2. Legt ein Python-Venv an und installiert die Abhängigkeiten (nur beim
   ersten Mal).
3. Indiziert alle gefundenen Dateien in den lokalen Chroma-Store und
   meldet die Anzahl.
4. Fragt, **welcher Modus** (A — Simulation, B — Karteikarten, C — Aufbau)
   plus modusspezifisches Setup.
5. Startet den gewählten Modus.

### Optional: Abhängigkeiten vorab installieren

Wer nicht warten will, bis die Aktivierungsrunde das Venv anlegt, kann es
auch von Hand machen (die Aktivierungsrunde überspringt diesen Schritt
dann):

```bash
cd skills/kolloquium/scripts
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Kolloquium durchführen

Nach der Aktivierungsrunde (siehe Quickstart Schritt 5) läuft der gewählte
Modus. Was in der Session passiert, steckt in `skills/kolloquium/SKILL.md`:
Modus A führt ein fließendes Gespräch, Modus B erzeugt Karteikarten im
gewünschten Format, Modus C erklärt interaktiv die Architektur des Skills.

Fortsetzen: mit "weiter" / "continue" ohne Neu-Indizierung in dieselbe
Session zurückkehren. Abbrechen: "stop" / "exit exam" / "ich will aufhören".

## Wie das Grounding funktioniert

Vor jeder Frage läuft pro Zug:

```bash
skills/kolloquium/scripts/.venv/bin/python skills/kolloquium/scripts/retrieve.py "<konzept>" --k 5
```

Das zurückgegebene JSON (`page`, `source`, `text`, `score`) ist das
abgeschlossene Universum für diese Frage. Wenn keine Passage die
Grounding-Schwelle erreicht, weigert sich der Agent, eine Frage zu erfinden,
und sagt das auch. Vollständige Regeln in `skills/kolloquium/SKILL.md`.

## Status

Gerüst steht — Index- und Retrieval-Skripte sind funktionierendes Python. Die
Prüfer-Persona lebt vollständig im SKILL.md-Prompt. Kein Server, kein Daemon,
kein externer API-Key nötig (Embeddings laufen lokal über
`sentence-transformers`; das LLM ist dasselbe, das opencode ohnehin nutzt).
