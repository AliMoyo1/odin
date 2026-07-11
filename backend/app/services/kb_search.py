from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.embeddings import embed_query, get_active_config


@dataclass
class SearchResult:
    chunk_id: str
    document_id: str
    file_name: str
    content: str
    page_number: int | None
    section_ref: str | None
    distance: float
    citation: str


async def search(
    session: AsyncSession,
    user_id: str,
    query: str,
    project_id: str | None = None,
    k: int = 5,
) -> list[SearchResult]:
    """Semantic search over knowledge base. Returns up to k results."""
    config = await get_active_config(session)
    if config is None:
        return []

    if not settings.OPENAI_API_KEY:
        return []

    qvec = await embed_query(query, config)
    qvec_str = "[" + ",".join(f"{v:.8f}" for v in qvec) + "]"

    project_filter = ""
    params: dict = {"uid": user_id, "qvec": qvec_str, "lim": 10}
    if project_id:
        project_filter = "AND kd.project_id = :project_id"
        params["project_id"] = project_id

    rows = (await session.execute(
        text(f"""
            SELECT
                kc.id AS chunk_id,
                kc.document_id,
                kd.file_name,
                kc.content,
                kc.page_number,
                kc.section_ref,
                (kc.embedding <=> CAST(:qvec AS vector)) AS distance
            FROM knowledge_chunks kc
            JOIN knowledge_documents kd ON kd.id = kc.document_id
            WHERE kd.user_id = :uid
              AND kd.processed = TRUE
              {project_filter}
            ORDER BY kc.embedding <=> CAST(:qvec AS vector)
            LIMIT :lim
        """),
        params,
    )).mappings().all()

    candidates = [
        {
            "chunk_id": str(r["chunk_id"]),
            "document_id": str(r["document_id"]),
            "file_name": r["file_name"],
            "content": r["content"],
            "page_number": r["page_number"],
            "section_ref": r["section_ref"],
            "distance": float(r["distance"]),
        }
        for r in rows
    ]

    if settings.RERANK_ENABLED and candidates:
        from app.services.rerank import rerank as _rerank
        candidates = _rerank(query, candidates, top_k=k)
    else:
        candidates = candidates[:k]

    results: list[SearchResult] = []
    for c in candidates:
        if c["page_number"] is not None:
            citation = f"[Source: {c['file_name']}, p.{c['page_number']}]"
        elif c["section_ref"]:
            citation = f"[Source: {c['file_name']}, {c['section_ref']}]"
        else:
            citation = f"[Source: {c['file_name']}]"

        results.append(SearchResult(
            chunk_id=c["chunk_id"],
            document_id=c["document_id"],
            file_name=c["file_name"],
            content=c["content"],
            page_number=c["page_number"],
            section_ref=c["section_ref"],
            distance=c["distance"],
            citation=citation,
        ))

    return results
