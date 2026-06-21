#!/usr/bin/env python3
"""Index a PDF into a local Chroma vector store for retrieval.

Each chunk stores its source PDF path and page number, so the examiner agent
can cite the exact passage it grounds a question on.

Usage:
    python index_pdf.py <pdf_path> [--index-dir DIR] [--chunk-size N] [--overlap N]

Output is written to the Chroma collection `kolloquium_passages` inside the
index directory (default: ../index relative to this script).
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INDEX_DIR = SCRIPT_DIR.parent / "index"
COLLECTION_NAME = "kolloquium_passages"
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pdf_path", type=Path, help="PDF file to index")
    p.add_argument(
        "--index-dir",
        type=Path,
        default=DEFAULT_INDEX_DIR,
        help=f"Chroma DB directory (default: {DEFAULT_INDEX_DIR})",
    )
    p.add_argument("--chunk-size", type=int, default=500, help="Tokens per chunk (approx chars)")
    p.add_argument("--overlap", type=int, default=80, help="Overlap between chunks (chars)")
    p.add_argument("--force", action="store_true", help="Re-index even if PDF already indexed")
    return p.parse_args()


def extract_pages(pdf_path: Path) -> list[tuple[int, str]]:
    """Return list of (page_number, text). Page numbers are 1-indexed."""
    reader = PdfReader(str(pdf_path))
    pages: list[tuple[int, str]] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append((i, text))
    return pages


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Greedy fixed-size chunker with overlap. Size is in characters."""
    if len(text) <= size:
        return [text] if text else []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
        if start >= len(text):
            break
    return chunks


def pdf_signature(pdf_path: Path) -> str:
    """Stable signature for dedup: path + mtime + size."""
    stat = pdf_path.stat()
    raw = f"{pdf_path.resolve()}|{stat.st_mtime_ns}|{stat.st_size}".encode()
    return hashlib.sha1(raw).hexdigest()  # nosec: used as dedup key, not security


def main() -> int:
    args = parse_args()
    pdf_path: Path = args.pdf_path
    if not pdf_path.is_file():
        print(f"error: PDF not found: {pdf_path}", file=sys.stderr)
        return 1

    args.index_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(args.index_dir))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Kolloquium examiner passages"},
    )

    sig = pdf_signature(pdf_path)
    existing = collection.get(where={"source_sig": sig}) if not args.force else None
    if existing and existing["ids"]:
        print(f"already indexed: {pdf_path.name} ({len(existing['ids'])} chunks). Use --force to re-index.")
        return 0

    print(f"loading embedder: {EMBED_MODEL}")
    embedder = SentenceTransformer(EMBED_MODEL)

    print(f"extracting pages from {pdf_path.name}")
    pages = extract_pages(pdf_path)
    if not pages:
        print("error: no extractable text in PDF (scanned PDFs need OCR first)", file=sys.stderr)
        return 2

    docs: list[str] = []
    metas: list[dict] = []
    ids: list[str] = []
    for page_no, text in pages:
        for j, chunk in enumerate(chunk_text(text, args.chunk_size, args.overlap)):
            if not chunk.strip():
                continue
            docs.append(chunk)
            metas.append(
                {
                    "source_pdf": str(pdf_path.resolve()),
                    "source_name": pdf_path.name,
                    "page": page_no,
                    "chunk_index": j,
                    "source_sig": sig,
                }
            )
            ids.append(f"{sig}::p{page_no}::c{j}")

    print(f"embedding {len(docs)} chunks...")
    vectors = embedder.encode(docs, show_progress_bar=True, convert_to_numpy=True).tolist()
    collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=vectors)

    print(f"done: {len(docs)} chunks stored in {args.index_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
