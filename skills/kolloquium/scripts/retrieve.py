#!/usr/bin/env python3
"""Die relevantesten PDF-Passagen für eine Query abrufen.

Gibt JSON auf stdout zurück, damit der opencode-Agent es determiniert
konsumieren kann.

Aufruf:
    python retrieve.py "<query>" [--index-dir VERZ] [--k N] [--pdf NAME]

Ausgabe (JSON-Array):
    [
      {
        "page": 12,
        "source": "script.pdf",
        "text": "...",
        "score": 0.81
      },
      ...
    ]

Exit-Codes:
    0  Erfolg (kann null Ergebnisse haben)
    1  Query leer
    2  Index nicht gefunden / leer
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INDEX_DIR = SCRIPT_DIR.parent / "index"
COLLECTION_NAME = "kolloquium_passages"
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("query", type=str, help="Suchanfrage")
    p.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    p.add_argument("--k", type=int, default=5, help="Top-k Passagen zurückgeben")
    p.add_argument("--pdf", type=str, default=None, help="Auf einen Quell-PDF-Dateinamen einschränken")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.query.strip():
        print(json.dumps({"error": "leere Query"}))
        return 1

    if not args.index_dir.exists():
        print(json.dumps({"error": f"Index-Verzeichnis nicht gefunden: {args.index_dir}. Zuerst index_corpus.py ausführen."}))
        return 2

    client = chromadb.PersistentClient(path=str(args.index_dir))
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        print(json.dumps({"error": f"Collection '{COLLECTION_NAME}' nicht gefunden. Zuerst index_corpus.py ausführen."}))
        return 2

    if collection.count() == 0:
        print(json.dumps({"error": "Index ist leer"}))
        return 2

    embedder = SentenceTransformer(EMBED_MODEL)
    query_vec = embedder.encode([args.query], convert_to_numpy=True, normalize_embeddings=True).tolist()

    where = {"source_name": args.pdf} if args.pdf else None
    res = collection.query(
        query_embeddings=query_vec,
        n_results=args.k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]
    # Chroma liefert quadrierte L2-Distanz; in Ähnlichkeit in [0,1] umrechnen
    out = []
    for doc, meta, dist in zip(docs, metas, dists):
        sim = max(0.0, 1.0 - dist / 2.0)
        out.append(
            {
                "page": meta.get("page"),
                "source": meta.get("source_name"),
                "text": doc,
                "score": round(sim, 4),
            }
        )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
