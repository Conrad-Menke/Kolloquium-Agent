# Kolloqium-Agent

An opencode skill that turns a corpus of PDFs into an **NRW Kolloquium** coach.
Built for the second-state exam (`Vorbereitungsdienst` / `Referendariat`).

The skill runs in three modes:

- **Mode A — Simulation**: a dynamic examiner conversation calibrated to the
  real NRW format. You open with a self-chosen *Kurzvortrag*; the agent picks
  up the "lose Enden" you leave and develops a flowing conversation across the
  Handlungsfelder, weaving empirical grounding with practical experience.
- **Mode B — Karteikarten**: produces study flashcards. Each card has a
  fictional examiner question, 3–5 answer keywords, and the exact source
  passage from your PDFs.
- **Mode C — Aufbau (Build-your-own tutor)**: the agent switches hats from
  examiner → coach/mentor and walks you through how this skill was built and
  how to fork it for your own use case (other exam format, other language,
  research papers instead of PDFs, Anki export, …). Mode C reads this repo's
  actual files rather than reciting from memory.

Every question and every card is **anchored in retrieved passages**. If the
corpus does not support a question, the agent says so instead of inventing one.
This skill enforces grounding by giving the agent access to **only** the
passages a retrieval step returns.

## Layout

```
.
├── AGENTS.md                       # Agent instructions (repo-level)
├── opencode.json                   # opencode config + permission rules
├── skills/
│   └── kolloquium/
│       ├── SKILL.md                # The examiner skill (persona + rules)
│       ├── scripts/
│       │   ├── index_corpus.py     # Parse + chunk + embed PDF/DOCX → Chroma
│       │   ├── retrieve.py         # Query → JSON passages
│       │   └── requirements.txt
│       ├── data/                   # PDFs/DOCX land here (gitignored)
│       └── index/                  # Chroma DB (gitignored)
```

## Install

1. Clone and (optionally) install dependencies ahead of time. The skill will
   also do this on first activation:

   ```bash
   cd skills/kolloquium/scripts
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Activate the skill in opencode. Either:

   - Symlink the skill into your opencode config dir:

     ```bash
     ln -s "$(pwd)/skills/kolloquium" \
           "$HOME/.config/opencode/skills/kolloquium"
     ```

   - Or run opencode from the repo root and reference the skill path directly.

## Running a Kolloquium

Start a session with any trigger phrase, e.g.:

> "Führe ein Kolloquium mit mir."

The skill then runs an **activation round**:

1. Asks for the folder or PDF file(s) to load (recursive for folders).
2. Verifies / creates the venv and installs requirements (first time only).
3. Indexes every PDF found into the local Chroma store and reports counts.
4. Asks **which mode** (A — Simulation, B — Karteikarten, C — Aufbau) plus
   mode-specific setup (Kurzvortrag topic / number of cards + output format /
   target use case to adapt for).
5. Begins the chosen mode.

Continuation: re-activating with "weiter" / "continue" resumes without
re-indexing.

## How grounding works

Each turn, before asking anything, the agent runs:

```bash
python retrieve.py "<concept>" --k 5
```

The returned JSON (`page`, `source`, `text`, `score`) is the closed universe
for that question. If no passage scores above the grounding threshold, the
agent refuses to fabricate a question and says so. Full rules in
`skills/kolloquium/SKILL.md`.

## Status

Skeleton scaffolded — index and retrieval scripts are functional Python. The
examiner persona lives entirely in the SKILL.md prompt. No server, no daemon,
no external API key required (embeddings run locally via
`sentence-transformers`; the LLM is whatever opencode is already using).
