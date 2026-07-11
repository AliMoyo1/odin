from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.models import Memory
from app.services.embeddings import embed_query, get_active_config

logger = logging.getLogger(__name__)

_NEAR_DUPLICATE_THRESHOLD = 0.15
_CONFLICT_THRESHOLD = 0.30
_RECALL_CUTOFF = 0.55
_MAX_VALUE_LEN = 500

_CREDENTIAL_WORDS = {"key", "token", "password", "secret", "passwd", "apikey"}


@dataclass
class RecalledMemory:
    id: str
    key: str | None
    value: str
    distance: float
    formatted: str


def _vec_str(vec: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in vec) + "]"


def _strip_credentials(value: str) -> bool:
    """Return True if the value looks like it contains a credential and should be dropped."""
    lower = value.lower()
    for word in _CREDENTIAL_WORDS:
        if word in lower:
            return True
    return False


async def store_explicit(
    session: AsyncSession,
    user_id: str,
    key: str,
    value: str,
) -> Memory:
    """Embed and store an explicit memory. Updates near-duplicate rather than inserting."""
    value = value[:_MAX_VALUE_LEN]

    config = await get_active_config(session)
    if config is None or not settings.OPENAI_API_KEY:
        m = Memory(
            user_id=user_id,
            memory_type="explicit",
            key=key,
            value=value,
            extra_meta={"status": "active", "origin": "explicit"},
        )
        session.add(m)
        await session.commit()
        await session.refresh(m)
        return m

    vec = await embed_query(value, config)
    vec_s = _vec_str(vec)

    row = (await session.execute(
        text("""
            SELECT id, (embedding <=> CAST(:qvec AS vector)) AS dist
            FROM memories
            WHERE user_id = :uid
              AND metadata->>'status' = 'active'
              AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:qvec AS vector)
            LIMIT 1
        """),
        {"uid": user_id, "qvec": vec_s},
    )).mappings().first()

    if row and row["dist"] < _NEAR_DUPLICATE_THRESHOLD:
        result = await session.execute(select(Memory).where(Memory.id == row["id"]))
        m = result.scalar_one()
        m.key = key
        m.value = value
        m.embedding = vec
        m.extra_meta = {**(m.extra_meta or {}), "status": "active", "origin": "explicit"}
        flag_modified(m, "extra_meta")
        await session.commit()
        await session.refresh(m)
        return m

    m = Memory(
        user_id=user_id,
        memory_type="explicit",
        key=key,
        value=value,
        embedding=vec,
        extra_meta={"status": "active", "origin": "explicit"},
    )
    session.add(m)
    await session.commit()
    await session.refresh(m)
    return m


async def recall(
    session: AsyncSession,
    user_id: str,
    query: str,
    k: int = 5,
) -> list[RecalledMemory]:
    """Embed query and return active memories within the distance cutoff."""
    config = await get_active_config(session)
    if config is None or not settings.OPENAI_API_KEY:
        return []

    vec = await embed_query(query, config)
    vec_s = _vec_str(vec)

    rows = (await session.execute(
        text("""
            SELECT id, key, value,
                   (embedding <=> CAST(:qvec AS vector)) AS distance
            FROM memories
            WHERE user_id = :uid
              AND metadata->>'status' = 'active'
              AND embedding IS NOT NULL
              AND (embedding <=> CAST(:qvec AS vector)) < :cutoff
            ORDER BY embedding <=> CAST(:qvec AS vector)
            LIMIT :k
        """),
        {"uid": user_id, "qvec": vec_s, "cutoff": _RECALL_CUTOFF, "k": k},
    )).mappings().all()

    ids = [str(r["id"]) for r in rows]
    if ids:
        # Fire-and-forget: do not await on the hot path
        asyncio.ensure_future(_track_access(user_id, ids))

    result: list[RecalledMemory] = []
    for r in rows:
        key = r["key"] or ""
        formatted = f"{key}: {r['value']}" if key else r["value"]
        result.append(RecalledMemory(
            id=str(r["id"]),
            key=r["key"],
            value=r["value"],
            distance=float(r["distance"]),
            formatted=formatted,
        ))
    return result


async def _track_access(user_id: str, ids: list[str]) -> None:
    from app.db import async_session as _sm
    try:
        async with _sm() as session:
            await session.execute(
                text("""
                    UPDATE memories
                    SET access_count = access_count + 1,
                        last_accessed_at = :now
                    WHERE id = ANY(:ids)
                """),
                {"ids": ids, "now": datetime.now(timezone.utc)},
            )
            await session.commit()
    except Exception:
        logger.exception("memory: access tracking failed for %s", ids)


async def suggest(
    session: AsyncSession,
    user_id: str,
    value: str,
    conversation_id: str | None = None,
) -> Memory | None:
    """Surface an implicitly extracted memory as a pending suggestion."""
    value = value[:_MAX_VALUE_LEN]
    if _strip_credentials(value):
        return None

    config = await get_active_config(session)
    if config is None or not settings.OPENAI_API_KEY:
        return None

    vec = await embed_query(value, config)
    vec_s = _vec_str(vec)

    rows = (await session.execute(
        text("""
            SELECT id, metadata, (embedding <=> CAST(:qvec AS vector)) AS dist
            FROM memories
            WHERE user_id = :uid
              AND metadata->>'status' = 'active'
              AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:qvec AS vector)
            LIMIT 1
        """),
        {"uid": user_id, "qvec": vec_s},
    )).mappings().all()

    conflict_with: str | None = None

    if rows:
        nearest = rows[0]
        dist = float(nearest["dist"])
        meta = nearest["metadata"] or {}

        if dist < _NEAR_DUPLICATE_THRESHOLD:
            return None  # Duplicate of an active memory; skip

        if dist < _CONFLICT_THRESHOLD and meta.get("origin") == "explicit":
            conflict_with = str(nearest["id"])

    extra: dict = {
        "status": "suggested",
        "origin": "implicit",
    }
    if conflict_with:
        extra["conflict_with"] = conflict_with
    if conversation_id:
        extra["suggested_from_conversation"] = conversation_id

    m = Memory(
        user_id=user_id,
        memory_type="implicit",
        key=None,
        value=value,
        embedding=vec,
        approved=False,
        extra_meta=extra,
    )
    session.add(m)
    await session.commit()
    await session.refresh(m)
    return m


async def approve_suggestion(session: AsyncSession, memory_id: str, user_id: str) -> Memory:
    result = await session.execute(
        select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
    )
    m = result.scalar_one_or_none()
    if m is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Memory not found")
    m.approved = True
    m.extra_meta = {**(m.extra_meta or {}), "status": "active"}
    flag_modified(m, "extra_meta")
    await session.commit()
    await session.refresh(m)
    return m


async def reject_suggestion(session: AsyncSession, memory_id: str, user_id: str) -> None:
    result = await session.execute(
        select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
    )
    m = result.scalar_one_or_none()
    if m is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Memory not found")
    await session.delete(m)
    await session.commit()


async def archive(session: AsyncSession, memory_id: str, user_id: str) -> Memory:
    result = await session.execute(
        select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
    )
    m = result.scalar_one_or_none()
    if m is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Memory not found")
    m.extra_meta = {**(m.extra_meta or {}), "status": "archived"}
    flag_modified(m, "extra_meta")
    await session.commit()
    await session.refresh(m)
    return m


async def list_memories(
    session: AsyncSession,
    user_id: str,
    status: str = "active",
) -> list[Memory]:
    result = await session.execute(
        text("""
            SELECT id FROM memories
            WHERE user_id = :uid
              AND metadata->>'status' = :status
            ORDER BY updated_at DESC
        """),
        {"uid": user_id, "status": status},
    )
    ids = [str(r[0]) for r in result.all()]
    if not ids:
        return []
    result2 = await session.execute(
        select(Memory).where(Memory.id.in_(ids))
    )
    by_id = {m.id: m for m in result2.scalars().all()}
    return [by_id[i] for i in ids if i in by_id]


async def get_stale_memories(session: AsyncSession, user_id: str) -> list[Memory]:
    """Active memories with access_count=0 created more than 90 days ago."""
    result = await session.execute(
        text("""
            SELECT id FROM memories
            WHERE user_id = :uid
              AND metadata->>'status' = 'active'
              AND access_count = 0
              AND created_at < (now() - interval '90 days')
            ORDER BY created_at ASC
        """),
        {"uid": user_id},
    )
    ids = [str(r[0]) for r in result.all()]
    if not ids:
        return []
    result2 = await session.execute(select(Memory).where(Memory.id.in_(ids)))
    return list(result2.scalars().all())


async def count_active(session: AsyncSession, user_id: str) -> int:
    result = await session.execute(
        text("SELECT COUNT(*) FROM memories WHERE user_id = :uid AND metadata->>'status' = 'active'"),
        {"uid": user_id},
    )
    return int(result.scalar() or 0)
