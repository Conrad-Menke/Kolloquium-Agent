#!/usr/bin/env python3
"""Index PDFs and DOCX files into a local Chroma vector store for retrieval.

Accepts either a single file or a directory (scanned recursively for supported
formats). Each chunk stores its source file path and page number when
available, so the examiner agent can cite the exact passage it grounds a
question on.

Supported formats:
    .pdf   — page number preserved (1-indexed)
    .docx  — no native pages; page is None, citation uses filename only

Usage:
    python index_corpus.py <path> [--index-dir DIR] [--chunk-size N] [--overlap N]

<path>  A supported file, or a folder searched recursively for supported files.

Output is written to the Chroma collection `kolloquium_passages` inside the
index directory (default: ../index relative to this script).

Exit codes:
    0  at least one file indexed (or already up to date)
    1  path not found / no supported files found
    2  one or more files had no extractable text
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
SUPPORTED_EXTS = {".pdf", ".docx"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", type=Path, help="File or folder to index")
    p.add_argument(
        "--index-dir",
        type=Path,
        default=DEFAULT_INDEX_DIR,
        help=f"Chroma DB directory (default: {DEFAULT_INDEX_DIR})",
    )
    p.add_argument("--chunk-size", type=int, default=500, help="Chars per chunk")
    p.add_argument("--overlap", type=int, default=80, help="Overlap between chunks (chars)")
    p.add_argument("--force", action="store_true", help="Re-index even if file already indexed")
    return p.parse_args()


def find_sources(path: Path) -> list[Path]:
    """Return supported files to index. Accepts a single file or a directory
    (recursive)."""
    if path.is_file():
        return [path] if path.suffix.lower() in SUPPORTED_EXTS else []
    if path.is_dir():
        return sorted(p for p in path.rglob("*") if p.suffix.lower() in SUPPORTED_EXTS)
    return []


def extract_pages_pdf(pdf_path: Path) -> list[tuple[int, str]]:
    """Return list of (page_number, text). Page numbers are 1-indexed."""
    reader = PdfReader(str(pdf_path))
    pages: list[tuple[int, str]] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append((i, text))
    return pages


def extract_text_docx(docx_path: Path) -> list[tuple[int | None, str]]:
    """Return whole DOCX as a single logical block. DOCX has no native pages,
    so page is None — citation uses filename only."""
    from docx import Document

    doc = Document(str(docx_path))
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [(None, text)] if text else []


def extract(file_path: Path) -> list[tuple[int | None, str]]:
    """Dispatch on extension. Returns list of (page|None, text)."""
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        return extract_pages_pdf(file_path)
    if ext == ".docx":
        return extract_text_docx(file_path)
    return []


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


def file_signature(file_path: Path) -> str:
    """Stable signature for dedup: path + mtime + size."""
    stat = file_path.stat()
    raw = f"{file_path.resolve()}|{stat.st_mtime_ns}|{stat.st_size}".encode()
    return hashlib.sha1(raw).hexdigest()  # nosec: dedup key, not security


def index_one(
    file_path: Path,
    embedder: SentenceTransformer,
    collection,
    chunk_size: int,
    overlap: int,
    force: bool,
) -> tuple[bool, str]:
    """Index a single file. Returns (ok, message)."""
    sig = file_signature(file_path)
    if not force:
        existing = collection.get(where={"source_sig": sig})
        if existing and existing["ids"]:
            return True, f"already indexed: {file_path.name} ({len(existing['ids'])} chunks), skip"

    blocks = extract(file_path)
    if not blocks:
        return False, f"no extractable text in {file_path.name} (scanned PDF needs OCR)"

    docs: list[str] = []
    metas: list[dict] = []
    ids: list[str] = []
    for block_index, (page_no, text) in enumerate(blocks):
        for j, chunk in enumerate(chunk_text(text, chunk_size, overlap)):
            if not chunk.strip():
                continue
            docs.append(chunk)
            metas.append(
                {
                    "source_file": str(file_path.resolve()),
                    "source_name": file_path.name,
                    "source_ext": file_path.suffix.lower().lstrip("."),
                    "page": page_no,
                    "block_index": block_index,
                    "chunk_index": j,
                    "source_sig": sig,
                }
            )
            page_part = f"p{page_no}" if page_no is not None else f"b{block_index}"
            ids.append(f"{sig}::{page_part}::c{j}")

    if not docs:
        return False, f"all chunks empty in {file_path.name}"

    vectors = embedder.encode(docs, show_progress_bar=False, convert_to_numpy=True).tolist()
    collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=vectors)
    return True, f"indexed {len(docs)} chunks from {file_path.name}"


def main() -> int:
    args = parse_args()
    path: Path = args.path
    if not path.exists():
        print(f"error: path not found: {path}", file=sys.stderr)
        return 1

    sources = find_sources(path)
    if not sources:
        print(
            f"error: no supported files ({', '.join(sorted(SUPPORTED_EXTS))}) found under {path}",
            file=sys.stderr,
        )
        return 1

    print(f"found {len(sources)} file(s) under {path}")
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
    for file_path in sources:
        ok, msg = index_one(
            file_path, embedder, collection, args.chunk_size, args.overlap, args.force
        )
        print(f"  - {msg}")
        if ok:
            ok_count += 1
        else:
            fail_count += 1
            if "OCR" in msg or "no extractable text" in msg:
                had_text_error = True

    total_chunks = collection.count()
    print(f"done: {ok_count} ok, {fail_count} failed. Total chunks in index: {total_chunks}")
    if had_text_error and fail_count == len(sources):
        return 2
    return 0 if ok_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
