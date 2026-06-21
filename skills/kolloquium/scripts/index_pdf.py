#!/usr/bin/env python3
"""Index one or more PDFs into a local Chroma vector store for retrieval.

Accepts either a single PDF file or a directory (scanned recursively for
`*.pdf`). Each chunk stores its source PDF path and page number, so the
examiner agent can cite the exact passage it grounds a question on.

Usage:
    python index_pdf.py <path> [--index-dir DIR] [--chunk-size N] [--overlap N]

<path>  A PDF file, or a folder that will be searched recursively for PDFs.

Output is written to the Chroma collection `kolloquium_passages` inside the
index directory (default: ../index relative to this script).

Exit codes:
    0  at least one PDF indexed (or already up to date)
    1  path not found / no PDFs found
    2  one or more PDFs had no extractable text
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
    p.add_argument("path", type=Path, help="PDF file or folder to index")
    p.add_argument(
        "--index-dir",
        type=Path,
        default=DEFAULT_INDEX_DIR,
        help=f"Chroma DB directory (default: {DEFAULT_INDEX_DIR})",
    )
    p.add_argument("--chunk-size", type=int, default=500, help="Chars per chunk")
    p.add_argument("--overlap", type=int, default=80, help="Overlap between chunks (chars)")
    p.add_argument("--force", action="store_true", help="Re-index even if PDF already indexed")
    return p.parse_args()


def find_pdfs(path: Path) -> list[Path]:
    """Return PDFs to index. Accepts a single file or a directory (recursive)."""
    if path.is_file():
        return [path] if path.suffix.lower() == ".pdf" else []
    if path.is_dir():
        return sorted(path.rglob("*.pdf"))
    return []


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
    return hashlib.sha1(raw).hexdigest()  # nosec: dedup key, not security


def index_one(
    pdf_path: Path,
    embedder: SentenceTransformer,
    collection,
    chunk_size: int,
    overlap: int,
    force: bool,
) -> tuple[bool, str]:
    """Index a single PDF. Returns (ok, message)."""
    sig = pdf_signature(pdf_path)
    if not force:
        existing = collection.get(where={"source_sig": sig})
        if existing and existing["ids"]:
            return True, f"already indexed: {pdf_path.name} ({len(existing['ids'])} chunks), skip"

    pages = extract_pages(pdf_path)
    if not pages:
        return False, f"no extractable text in {pdf_path.name} (scanned PDF needs OCR)"

    docs: list[str] = []
    metas: list[dict] = []
    ids: list[str] = []
    for page_no, text in pages:
        for j, chunk in enumerate(chunk_text(text, chunk_size, overlap)):
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

    if not docs:
        return False, f"all chunks empty in {pdf_path.name}"

    vectors = embedder.encode(docs, show_progress_bar=False, convert_to_numpy=True).tolist()
    collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=vectors)
    return True, f"indexed {len(docs)} chunks from {pdf_path.name}"


def main() -> int:
    args = parse_args()
    path: Path = args.path
    if not path.exists():
        print(f"error: path not found: {path}", file=sys.stderr)
        return 1

    pdfs = find_pdfs(path)
    if not pdfs:
        print(f"error: no PDFs found under {path}", file=sys.stderr)
        return 1

    print(f"found {len(pdfs)} PDF(s) under {path}")
    args.index_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(args.index_dir))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Kolloquium examiner passages"},
    )

    print(f"loading embedder: {EMBED_MODEL}")
    embedder = SentenceTransformer(EMBED_MODEL)

    ok_count = 0
    fail_count = 0
    had_text_error = False
    for pdf_path in pdfs:
        ok, msg = index_one(
            pdf_path, embedder, collection, args.chunk_size, args.overlap, args.force
        )
        print(f"  - {msg}")
        if ok:
            ok_count += 1
        else:
            fail_count += 1
            if "OCR" in msg:
                had_text_error = True

    total_chunks = collection.count()
    print(f"done: {ok_count} ok, {fail_count} failed. Total chunks in index: {total_chunks}")
    if had_text_error and fail_count == len(pdfs):
        return 2
    return 0 if ok_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
