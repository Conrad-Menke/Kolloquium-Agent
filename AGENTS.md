# Agent Instructions

## Project context

`Kolloqium-Agent`: opencode skill that turns a corpus of PDFs into a
conversational oral examiner. Lives in `skills/kolloquium/`. Read
`skills/kolloquium/SKILL.md` first when working on the examiner behavior.

## Working directory

Repo root is the working directory. Keep paths relative to root.

## Conventions

- One logical change per commit.
- Do not commit secrets, tokens, API keys, `.env`, PDFs, or the Chroma index.
- Python code targets 3.10+ (uses PEP 604 unions, `from __future__ import annotations`).
- Run `python -m py_compile` on changed `.py` files before committing if no
  test suite exists yet.

## Skill scripts

| Script | Purpose | Read-only? |
|--------|---------|-----------|
| `skills/kolloquium/scripts/index_pdf.py` | Parse + chunk + embed PDF into Chroma | Writes to `index/` |
| `skills/kolloquium/scripts/retrieve.py` | Query Chroma → JSON passages | Read-only |

Both scripts must remain **deterministic and side-effect-free apart from the
index dir**. The agent relies on them returning predictable JSON.

## Grounding rules (critical)

The examiner agent must never ask a question whose content is not supported by
retrieved passages. When modifying `SKILL.md`, preserve the grounding rules
verbatim in spirit — they are the whole point of this repo.

## What NOT to do

- Do not add a networked LLM call inside the scripts. The skill calls the LLM
  via opencode; the scripts only handle parsing + retrieval.
- Do not store PDFs or the Chroma index in git.
- Do not force-push or rewrite history unless explicitly asked.
- Do not install heavy dependencies without confirmation.
