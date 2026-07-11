from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.models import (
    EmbeddingConfig,
    KnowledgeChunk,
    KnowledgeDocument,
    Notification,
)
from app.services.chunker import chunk_document
from app.services.embeddings import embed_chunks, get_active_config
from app.services.events import publish_sync
from app.services.extract import extract
from app.services.file_service import resolve_in_workspace
from workers.celery_app import app as celery_app

logger = logging.getLogger(__name__)

_engine = create_async_engine(settings.DATABASE_URL, echo=False)
_sm = async_sessionmaker(_engine, expire_on_commit=False)

_NO_KEY_NOTIFIED_REDIS_KEY = "odin:kb:no_embed_key_notified"


@celery_app.task(name="index_document")
def index_document(document_id: str) -> None:
    asyncio.run(_async_index(document_id))


async def _async_index(document_id: str) -> None:
    async with _sm() as session:
        result = await session.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            logger.warning("index_document: document %s not found", document_id)
            return

        # Resolve file in sandbox
        try:
            file_path = resolve_in_workspace(doc.file_path)
        except ValueError:
            logger.error("index_document: unsafe path for document %s: %s", document_id, doc.file_path)
            return

        if not file_path.exists():
            logger.warning("index_document: file does not exist: %s", file_path)
            return

        # Idempotency: skip if content unchanged
        content_bytes = file_path.read_bytes()
        sha256 = hashlib.sha256(content_bytes).hexdigest()
        if doc.content_sha256 == sha256 and doc.processed:
            return

        # Check embedding config
        ec = await get_active_config(session)
        if ec is None:
            logger.error("index_document: no active embedding config")
            return

        # Guard: no API key
        if not settings.OPENAI_API_KEY:
            await _notify_no_key(session, doc.user_id)
            return

        # Extract text
        extension = file_path.suffix.lower().lstrip(".")
        blocks = extract(file_path)

        total_text = "".join(b.text for b in blocks)
        if len(total_text.strip()) < 50:
            # Scanned PDF or empty file: mark processed with warning
            doc.processed = True
            doc.extra_meta = {**(doc.extra_meta or {}), "warning": "no extractable text (scanned?)"}
            await session.commit()
            logger.info("index_document: %s: no extractable text, skipped embedding", doc.file_name)
            return

        # Chunk
        chunks = chunk_document(blocks, extension, doc.chunk_config)
        if not chunks:
            doc.processed = True
            await session.commit()
            return

        # Embed
        texts = [c.content for c in chunks]
        try:
            vectors = await embed_chunks(texts, ec)
        except Exception as exc:
            logger.error("index_document: embedding failed for %s: %s", doc.file_name, exc)
            raise

        # One transaction: delete old chunks, insert new, update document
        await session.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id)
        )

        new_chunks = [
            KnowledgeChunk(
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                page_number=chunk.page_number,
                section_ref=chunk.section_ref,
                embedding=vector,
            )
            for chunk, vector in zip(chunks, vectors)
        ]
        session.add_all(new_chunks)

        await session.execute(
            update(KnowledgeDocument)
            .where(KnowledgeDocument.id == document_id)
            .values(
                processed=True,
                indexed_at=datetime.now(timezone.utc),
                content_sha256=sha256,
                chunk_count=len(new_chunks),
                embedding_config_id=ec.id,
            )
        )

        n = Notification(
            user_id=doc.user_id,
            title=f"Indexed {doc.file_name}: {len(new_chunks)} chunks",
            category="hermes",
        )
        session.add(n)
        await session.commit()
        await session.refresh(n)

        publish_sync(
            f"events:{doc.user_id}",
            "notification.new",
            {"id": str(n.id), "title": n.title, "body": None, "category": "hermes"},
        )
        logger.info("index_document: indexed %s (%d chunks)", doc.file_name, len(new_chunks))


async def _notify_no_key(session, user_id: str) -> None:
    from app.services.events import _get_sync
    redis = _get_sync()
    key = f"{_NO_KEY_NOTIFIED_REDIS_KEY}:{user_id}"
    if redis.get(key):
        return
    redis.setex(key, 86400, "1")  # suppress for 24h

    n = Notification(
        user_id=user_id,
        title="Knowledge indexing disabled: no embedding key",
        category="system",
    )
    session.add(n)
    await session.commit()
    await session.refresh(n)
    publish_sync(
        f"events:{user_id}",
        "notification.new",
        {"id": str(n.id), "title": n.title, "body": None, "category": "system"},
    )
