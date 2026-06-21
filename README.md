# Kolloqium-Agent

An opencode skill that turns a corpus of PDFs into a **conversational oral
examiner** (German-style "Kolloquium" / "mündliche Prüfung").

The agent asks one grounded question at a time, listens to your answer,
acknowledges it, and follows up — like a qualified human examiner. Every
question is anchored in a passage retrieved from your PDFs. If the corpus does
not support a question, the agent says so instead of inventing one.

## Why

Oral exams need pacing, follow-ups, and fair probing. Static flashcard apps
don't do that. A grounded LLM agent does — as long as it cannot hallucinate.
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
│       │   ├── index_pdf.py        # Parse + chunk + embed PDF → Chroma
│       │   ├── retrieve.py         # Query → JSON passages
│       │   └── requirements.txt
│       ├── data/                   # PDFs land here (gitignored)
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
4. Optionally asks 1–2 focus questions (topics, depth).
5. Opens the exam with the first grounded question.

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
