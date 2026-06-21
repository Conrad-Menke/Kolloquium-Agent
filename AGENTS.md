# Agent Instructions

## Project context

Kolloqium-Agent: agent assisting with Kolloquium (seminar / conference /
colloquium) related tasks. Update this file as scope becomes concrete.

## Working directory

Repo root is the working directory. Keep all paths relative to root.

## Conventions

- Keep changes small and focused. One logical change per commit.
- Do not commit secrets, tokens, API keys, or `.env` files.
- Follow existing code style. If none exists yet, ask before introducing a new
  language or framework.
- Run lint / typecheck before committing if a toolchain is configured.

## Communication

- Be concise. Lead with the result, then the reasoning if asked.
- Surface assumptions explicitly before acting on them.

## What to do first

1. Confirm the project's language / runtime with the user.
2. Pick a package manager and lockfile strategy.
3. Scaffold the entry point and a minimal test.

## What NOT to do

- Do not force-push or rewrite history unless explicitly asked.
- Do not install heavy dependencies without confirmation.
- Do not delete files outside the repo root.
