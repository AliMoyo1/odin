from __future__ import annotations

from dataclasses import dataclass

import tiktoken

from app.services.extract import ExtractedBlock

_CODE_EXTS: frozenset[str] = frozenset({"py", "js", "ts"})


@dataclass
class ChunkRecord:
    chunk_index: int
    content: str
    page_number: int | None
    section_ref: str | None


def _resolve_config(extension: str, chunk_config: dict | None) -> tuple[int, int]:
    """Return (max_tokens, overlap) for the given extension + optional override."""
    if chunk_config and "max_tokens" in chunk_config:
        return int(chunk_config["max_tokens"]), int(chunk_config.get("overlap", 200))
    if extension in _CODE_EXTS:
        return 500, 100
    return 1000, 200


def _hard_split(text: str, max_tok: int, overlap: int) -> list[str]:
    """Split `text` into token windows of at most `max_tok` with `overlap` carry."""
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    if len(tokens) <= max_tok:
        stripped = text.strip()
        return [stripped] if stripped else []

    result: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tok, len(tokens))
        chunk = enc.decode(tokens[start:end])
        if chunk.strip():
            result.append(chunk)
        if end >= len(tokens):
            break
        start = end - overlap
    return result


def chunk_document(
    blocks: list[ExtractedBlock],
    extension: str,
    chunk_config: dict | None = None,
) -> list[ChunkRecord]:
    """Chunk extracted blocks into fixed-size token windows with overlap."""
    max_tok, overlap = _resolve_config(extension.lower().lstrip("."), chunk_config)

    result: list[ChunkRecord] = []
    idx = 0

    for block in blocks:
        if not block.text.strip():
            continue
        for sub in _hard_split(block.text, max_tok, overlap):
            result.append(ChunkRecord(
                chunk_index=idx,
                content=sub,
                page_number=block.page_number,
                section_ref=block.section_ref,
            ))
            idx += 1

    return result
