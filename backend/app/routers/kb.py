from __future__ import annotations

import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models.models import KnowledgeDocument, User
from app.services.file_service import resolve_in_workspace, workspace_root
from app.services.kb_search import search

router = APIRouter(prefix="/api/v1/kb", tags=["knowledge"])


class RegisterDocumentIn(BaseModel):
    file_path: str
    project_id: str | None = None


class NoteIn(BaseModel):
    title: str
    content: str
    project_id: str | None = None


class DocumentOut(BaseModel):
    id: str
    file_name: str
    file_path: str
    processed: bool
    chunk_count: int
    indexed_at: datetime | None
    project_id: str | None


class SearchIn(BaseModel):
    query: str
    project_id: str | None = None
    k: int = 5


class ChunkResult(BaseModel):
    chunk_id: str
    document_id: str
    file_name: str
    content: str
    page_number: int | None
    section_ref: str | None
    distance: float
    citation: str


@router.post("/documents", response_model=DocumentOut, status_code=201)
async def register_document(
    body: RegisterDocumentIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    try:
        file_path = resolve_in_workspace(body.file_path)
    except ValueError:
        raise HTTPException(400, "Invalid path")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(404, "File not found")

    rel_path = str(file_path.relative_to(workspace_root()))

    result = await session.execute(
        sa_select(KnowledgeDocument).where(
            KnowledgeDocument.user_id == user.id,
            KnowledgeDocument.file_path == rel_path,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        doc = KnowledgeDocument(
            user_id=user.id,
            project_id=body.project_id,
            file_path=rel_path,
            file_name=file_path.name,
            file_size=file_path.stat().st_size,
        )
        session.add(doc)
        await session.flush()

    await session.commit()
    await session.refresh(doc)

    from workers.indexing import index_document
    index_document.delay(doc.id)

    return _doc_to_out(doc)


@router.post("/notes", response_model=DocumentOut, status_code=201)
async def create_note(
    body: NoteIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    slug = re.sub(r"[^\w\-]", "-", body.title.lower()).strip("-") or "note"
    notes_dir = workspace_root() / "Knowledge" / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)

    note_path = notes_dir / f"{slug}.md"
    counter = 1
    while note_path.exists():
        note_path = notes_dir / f"{slug}-{counter}.md"
        counter += 1

    note_path.write_text(body.content, encoding="utf-8")
    rel_path = str(note_path.relative_to(workspace_root()))

    doc = KnowledgeDocument(
        user_id=user.id,
        project_id=body.project_id,
        file_path=rel_path,
        file_name=note_path.name,
        file_size=len(body.content.encode()),
    )
    session.add(doc)
    await session.flush()
    await session.commit()
    await session.refresh(doc)

    from workers.indexing import index_document
    index_document.delay(doc.id)

    return _doc_to_out(doc)


@router.get("/documents", response_model=list[DocumentOut])
async def list_documents(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    result = await session.execute(
        sa_select(KnowledgeDocument)
        .where(KnowledgeDocument.user_id == user.id)
        .order_by(KnowledgeDocument.created_at.desc())
    )
    return [_doc_to_out(d) for d in result.scalars().all()]


@router.post("/search", response_model=list[ChunkResult])
async def kb_search(
    body: SearchIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if not body.query.strip():
        raise HTTPException(400, "query must not be empty")
    results = await search(
        session,
        user_id=user.id,
        query=body.query,
        project_id=body.project_id,
        k=min(body.k, 20),
    )
    return [
        ChunkResult(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            file_name=r.file_name,
            content=r.content,
            page_number=r.page_number,
            section_ref=r.section_ref,
            distance=r.distance,
            citation=r.citation,
        )
        for r in results
    ]


def _doc_to_out(doc: KnowledgeDocument) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        file_name=doc.file_name,
        file_path=doc.file_path,
        processed=doc.processed,
        chunk_count=doc.chunk_count,
        indexed_at=doc.indexed_at,
        project_id=doc.project_id,
    )
