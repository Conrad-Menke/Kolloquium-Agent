# Agent-Anweisungen

## Projektkontext

`Kolloqium-Agent`: opencode-Skill, der einen Corpus an PDFs in einen
gesprächsorientierten mündlichen Prüfer verwandelt. Lebt in
`skills/kolloquium/`. `skills/kolloquium/SKILL.md` zuerst lesen, wenn am
Prüfer-Verhalten gearbeitet wird.

## Arbeitsverzeichnis

Repo-Root ist das Arbeitsverzeichnis. Pfade relativ zum Root halten.

## Konventionen

- Eine logische Änderung pro Commit.
- Keine Secrets, Tokens, API-Keys, `.env`, PDFs, DOCX oder den Chroma-Index
  committen.
- Python-Code zielt auf 3.10+ (nutzt PEP-604-Unions,
  `from __future__ import annotations`).
- `python -m py_compile` auf geänderten `.py`-Dateien ausführen, bevor
  committet wird, falls noch keine Test-Suite existiert.

## Skill-Skripte

| Skript | Zweck | Read-only? |
|--------|-------|-----------|
| `skills/kolloquium/scripts/index_corpus.py` | PDF/DOCX parsen + chunken + embedden in Chroma | Schreibt nach `index/` |
| `skills/kolloquium/scripts/retrieve.py` | Chroma abfragen → JSON-Passagen | Read-only |

Beide Skripte müssen **determiniert und nebenwirkungsfrei abgesehen vom
Index-Verzeichnis** bleiben. Der Agent verlässt sich darauf, dass sie
vorhersehbares JSON zurückgeben.

## Grounding-Regeln (kritisch)

Der Prüfer-Agent darf niemals eine Frage stellen, deren Inhalt nicht durch
abgerufene Passagen gestützt ist. Bei Änderungen an `SKILL.md` die
Grounding-Regeln inhaltlich wortwörtlich erhalten — sie sind der ganze Sinn
dieses Repos.

## Was NICHT zu tun ist

- Keinen netzwerkgestützten LLM-Aufruf innerhalb der Skripte einbauen. Der
  Skill ruft das LLM über opencode; die Skripte übernehmen nur Parsen +
  Retrieval (PDF + DOCX).
- Keine PDFs oder den Chroma-Index in git speichern.
- Nicht force-pushen oder die Commit-Historie umschreiben, außer wenn ausdrücklich
  darum gebeten.
- Keine schweren Abhängigkeiten ohne Bestätigung installieren.
