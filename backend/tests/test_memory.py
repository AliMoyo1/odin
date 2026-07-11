"""
Memory service end-to-end tests.
Runs against the real test database; embeddings are monkeypatched.
"""
from __future__ import annotations

import math
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.models import Memory, User
from app.security.passwords import hash_password

_MEM_EMAIL = "test_memory@odin.local"
_DIM = 1536

# Controlled unit vectors for exact distance assertions
_E0 = [1.0] + [0.0] * (_DIM - 1)
_E1 = [0.0, 1.0] + [0.0] * (_DIM - 2)  # orthogonal -> distance 1.0 from E0
# cos_sim([0.8, 0.6, ...], E0) = 0.8, so distance = 0.2 (in conflict range [0.15, 0.30))
_E_CONFLICT = [0.8, 0.6] + [0.0] * (_DIM - 2)

_embed_map: dict[str, list[float]] = {}


class _FakeConfig:
    id = "fake-config-id"
    model = "text-embedding-3-small"
    dimensions = _DIM
    is_active = True


async def _fake_embed_query(text: str, config: Any) -> list[float]:
    return _embed_map.get(text, _E1)


async def _fake_get_active_config(session: Any) -> _FakeConfig:
    return _FakeConfig()


@pytest_asyncio.fixture(scope="module")
async def mem_user():
    engine = create_async_engine(settings.DATABASE_URL)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as session:
        await session.execute(delete(User).where(User.email == _MEM_EMAIL))
        await session.commit()
        user = User(email=_MEM_EMAIL, password_hash=hash_password("MemTest123!"))
        session.add(user)
        await session.commit()
        await session.refresh(user)
        uid = user.id

    yield {"id": uid, "email": _MEM_EMAIL}

    async with sm() as session:
        await session.execute(delete(Memory).where(Memory.user_id == uid))
        await session.execute(delete(User).where(User.email == _MEM_EMAIL))
        await session.commit()
    await engine.dispose()


@pytest_asyncio.fixture
async def mem_session(mem_user):
    engine = create_async_engine(settings.DATABASE_URL)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as session:
        # Clean memories before each test
        await session.execute(delete(Memory).where(Memory.user_id == mem_user["id"]))
        await session.commit()
        yield session
    await engine.dispose()


def _patch_embeddings(monkeypatch):
    import app.services.memory_service as svc
    monkeypatch.setattr(svc, "embed_query", _fake_embed_query)
    monkeypatch.setattr(svc, "get_active_config", _fake_get_active_config)
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "fake-key")


@pytest.mark.asyncio
async def test_store_explicit_creates_memory(mem_user, mem_session, monkeypatch):
    _patch_embeddings(monkeypatch)
    _embed_map["User prefers dark mode"] = _E0

    from app.services.memory_service import store_explicit
    m = await store_explicit(mem_session, mem_user["id"], "theme", "User prefers dark mode")

    assert m.id is not None
    assert m.key == "theme"
    assert m.value == "User prefers dark mode"
    assert (m.extra_meta or {}).get("status") == "active"
    assert (m.extra_meta or {}).get("origin") == "explicit"


@pytest.mark.asyncio
async def test_store_explicit_near_duplicate_updates(mem_user, mem_session, monkeypatch):
    _patch_embeddings(monkeypatch)
    _embed_map["User uses vim"] = _E0
    _embed_map["User uses vim keybindings"] = _E0  # identical vector -> distance 0

    from app.services.memory_service import store_explicit
    m1 = await store_explicit(mem_session, mem_user["id"], "editor", "User uses vim")
    m2 = await store_explicit(mem_session, mem_user["id"], "editor_detail", "User uses vim keybindings")

    # Should update m1, not insert a new row
    assert m1.id == m2.id
    assert m2.key == "editor_detail"
    assert m2.value == "User uses vim keybindings"

    result = await mem_session.execute(
        select(Memory).where(Memory.user_id == mem_user["id"])
    )
    all_mems = result.scalars().all()
    assert len(all_mems) == 1


@pytest.mark.asyncio
async def test_recall_returns_matching(mem_user, mem_session, monkeypatch):
    _patch_embeddings(monkeypatch)
    _embed_map["User works in Python"] = _E0
    _embed_map["python programming language"] = _E0  # same vector -> distance 0

    from app.services.memory_service import recall, store_explicit
    await store_explicit(mem_session, mem_user["id"], "language", "User works in Python")

    results = await recall(mem_session, mem_user["id"], "python programming language", k=5)
    assert len(results) == 1
    assert results[0].value == "User works in Python"
    assert results[0].distance < 0.55


@pytest.mark.asyncio
async def test_recall_respects_cutoff(mem_user, mem_session, monkeypatch):
    _patch_embeddings(monkeypatch)
    # Store memory at E0, query at E1 (orthogonal -> distance 1.0 > cutoff 0.55)
    _embed_map["User likes coffee"] = _E0
    _embed_map["completely unrelated query xyz"] = _E1

    from app.services.memory_service import recall, store_explicit
    await store_explicit(mem_session, mem_user["id"], "beverage", "User likes coffee")

    results = await recall(mem_session, mem_user["id"], "completely unrelated query xyz", k=5)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_suggest_skips_credential(mem_user, mem_session, monkeypatch):
    _patch_embeddings(monkeypatch)

    from app.services.memory_service import suggest
    result = await suggest(mem_session, mem_user["id"], "API key = sk-abc123secret", "conv-1")
    assert result is None


@pytest.mark.asyncio
async def test_suggest_skips_credential_token(mem_user, mem_session, monkeypatch):
    _patch_embeddings(monkeypatch)

    from app.services.memory_service import suggest
    result = await suggest(mem_session, mem_user["id"], "auth token: Bearer eyJhb...", "conv-2")
    assert result is None


@pytest.mark.asyncio
async def test_suggest_deduplicates_active_memory(mem_user, mem_session, monkeypatch):
    _patch_embeddings(monkeypatch)
    _embed_map["User is located in London"] = _E0
    _embed_map["User lives in London"] = _E0  # same vector -> distance 0

    from app.services.memory_service import store_explicit, suggest
    await store_explicit(mem_session, mem_user["id"], "location", "User is located in London")

    result = await suggest(mem_session, mem_user["id"], "User lives in London", "conv-3")
    assert result is None  # Near-duplicate of active memory; should be skipped


@pytest.mark.asyncio
async def test_suggest_sets_conflict_with(mem_user, mem_session, monkeypatch):
    _patch_embeddings(monkeypatch)
    _embed_map["User prefers Python"] = _E0
    _embed_map["User mainly codes in JavaScript"] = _E_CONFLICT

    from app.services.memory_service import store_explicit, suggest
    explicit_mem = await store_explicit(mem_session, mem_user["id"], "lang", "User prefers Python")

    suggestion = await suggest(
        mem_session, mem_user["id"], "User mainly codes in JavaScript", "conv-4"
    )
    assert suggestion is not None
    assert (suggestion.extra_meta or {}).get("status") == "suggested"
    assert (suggestion.extra_meta or {}).get("conflict_with") == explicit_mem.id


@pytest.mark.asyncio
async def test_approve_suggestion_promotes_to_active(mem_user, mem_session, monkeypatch):
    _patch_embeddings(monkeypatch)
    _embed_map["User prefers tabs over spaces"] = _E1  # orthogonal -> no conflict

    from app.services.memory_service import approve_suggestion, suggest
    m = await suggest(mem_session, mem_user["id"], "User prefers tabs over spaces", "conv-5")
    assert m is not None
    assert (m.extra_meta or {}).get("status") == "suggested"

    approved = await approve_suggestion(mem_session, m.id, mem_user["id"])
    assert (approved.extra_meta or {}).get("status") == "active"
    assert approved.approved is True


@pytest.mark.asyncio
async def test_reject_suggestion_deletes_row(mem_user, mem_session, monkeypatch):
    _patch_embeddings(monkeypatch)
    _embed_map["User enjoys jazz music"] = _E1

    from app.services.memory_service import reject_suggestion, suggest
    m = await suggest(mem_session, mem_user["id"], "User enjoys jazz music", "conv-6")
    assert m is not None
    mem_id = m.id

    await reject_suggestion(mem_session, mem_id, mem_user["id"])

    result = await mem_session.execute(select(Memory).where(Memory.id == mem_id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_archive_sets_archived_status(mem_user, mem_session, monkeypatch):
    _patch_embeddings(monkeypatch)
    _embed_map["User has a standing desk"] = _E0

    from app.services.memory_service import archive, store_explicit
    m = await store_explicit(mem_session, mem_user["id"], "desk", "User has a standing desk")
    assert (m.extra_meta or {}).get("status") == "active"

    archived = await archive(mem_session, m.id, mem_user["id"])
    assert (archived.extra_meta or {}).get("status") == "archived"
