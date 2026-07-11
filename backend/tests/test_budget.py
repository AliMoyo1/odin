from __future__ import annotations

import pytest

from app.hermes.budget import (
    MAX_MEMORIES,
    MAX_RAG_CHUNKS,
    MIN_RAG_CHUNKS,
    SUMMARY_HISTORY_TAIL,
    build_budgeted_messages,
)
from app.hermes.types import ChatMessage


def _msg(role: str, content: str) -> ChatMessage:
    return ChatMessage(role=role, content=content)


def test_history_trimming_oldest_dropped():
    # Each message is ~1000 chars = ~258 estimated tokens. 50 * 258 = 12900 > 7160 ollama budget.
    history = [_msg("user", f"msg {i} " + ("x" * 990)) for i in range(50)]
    budgeted, info = build_budgeted_messages(
        system="system",
        history=history,
        memories=[],
        rag_chunks=[],
        provider="ollama",  # tight 8192 context
        max_tokens=1024,
    )
    assert len(budgeted) < len(history), "Should have trimmed history"
    # Newest messages are kept
    assert budgeted[-1].content == history[-1].content


def test_rag_trim_from_5_to_3():
    big_chunk = "x" * 2000
    chunks = [big_chunk] * 5
    history = [_msg("user", "hi")]
    budgeted, info = build_budgeted_messages(
        system="system",
        history=history,
        memories=[],
        rag_chunks=chunks,
        provider="ollama",
        max_tokens=1024,
    )
    assert info["rag_chunks"] <= MAX_RAG_CHUNKS
    if info["budget_remaining"] < 0:
        assert info["rag_chunks"] <= MIN_RAG_CHUNKS


def test_memories_capped_at_max():
    memories = [f"memory {i}" for i in range(20)]
    _, info = build_budgeted_messages(
        system="system",
        history=[_msg("user", "hello")],
        memories=memories,
        rag_chunks=[],
        provider="deepseek",
    )
    assert info["memory_count"] <= MAX_MEMORIES


def test_summary_substitution():
    long_history = [_msg("user" if i % 2 == 0 else "assistant", f"turn {i}") for i in range(30)]
    summary = "The user asked about various topics."
    budgeted, info = build_budgeted_messages(
        system="system",
        history=long_history,
        memories=[],
        rag_chunks=[],
        conversation_summary=summary,
        provider="deepseek",
    )
    # Should have a summary message at the start
    contents = [m.content for m in budgeted]
    assert any(summary in str(c) for c in contents), "Summary should appear in messages"
    # Tail messages should be present
    assert budgeted[-1].content == long_history[-1].content


def test_full_history_fits_without_trim():
    history = [_msg("user", "hi"), _msg("assistant", "hello")]
    budgeted, info = build_budgeted_messages(
        system="short",
        history=history,
        memories=[],
        rag_chunks=[],
        provider="anthropic",
    )
    assert len(budgeted) == 2
    assert info["budget_remaining"] > 0
