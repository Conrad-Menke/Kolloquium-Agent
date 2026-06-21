#!/usr/bin/env python3
"""Retrieve the most relevant PDF passages for a query.

Returns JSON to stdout so the opencode agent can consume it deterministically.

Usage:
    python retrieve.py "<query>" [--index-dir DIR] [--k N] [--pdf NAME]

Output (JSON array):
    [
      {
        "page": 12,
        "source": "script.pdf",
        "text": "...",
        "score": 0.81
      },
      ...
    ]

Exit codes:
    0  success (may have zero results)
    1  query empty
    2  index not found / empty
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
    p.add_argument("query", type=str, help="Search query")
    p.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    p.add_argument("--k", type=int, default=5, help="Top-k passages to return")
    p.add_argument("--pdf", type=str, default=None, help="Restrict to one source PDF filename")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.query.strip():
        print(json.dumps({"error": "empty query"}))
        return 1

    if not args.index_dir.exists():
        print(json.dumps({"error": f"index dir not found: {args.index_dir}. Run index_pdf.py first."}))
        return 2

    client = chromadb.PersistentClient(path=str(args.index_dir))
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        print(json.dumps({"error": f"collection '{COLLECTION_NAME}' not found. Run index_pdf.py first."}))
        return 2

    if collection.count() == 0:
        print(json.dumps({"error": "index is empty"}))
        return 2

    embedder = SentenceTransformer(EMBED_MODEL)
    query_vec = embedder.encode([args.query], convert_to_numpy=True).tolist()

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
    # chroma returns squared L2 distance; convert to similarity in [0,1]
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
