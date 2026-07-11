from __future__ import annotations

from app.hermes.types import ChatMessage

CONTEXT_LIMITS = {
    "deepseek": 64000,
    "anthropic": 200000,
    "gemini": 1000000,
    "openai": 128000,
    "ollama": 8192,
}

DEFAULT_MAX_TOKENS = 4096
MAX_RAG_CHUNKS = 5
MIN_RAG_CHUNKS = 3
MAX_MEMORIES = 5
SUMMARY_HISTORY_TAIL = 10


def _estimate(text: str) -> int:
    return len(text) // 4 + 8


def _msg_tokens(msg: ChatMessage) -> int:
    if isinstance(msg.content, str):
        return _estimate(msg.content)
    if isinstance(msg.content, list):
        total = 8
        for block in msg.content:
            if isinstance(block, dict):
                total += _estimate(str(block.get("text") or block.get("thinking") or ""))
        return total
    return 8


def build_budgeted_messages(
    system: str,
    history: list[ChatMessage],
    memories: list[str],
    rag_chunks: list[str],
    provider: str = "deepseek",
    max_tokens: int = DEFAULT_MAX_TOKENS,
    conversation_summary: str | None = None,
) -> tuple[list[ChatMessage], dict]:
    context_limit = CONTEXT_LIMITS.get(provider, 64000)
    budget = context_limit - max_tokens - _estimate(system)

    # Cap memories
    used_memories = memories[:MAX_MEMORIES]
    memory_tokens = sum(_estimate(m) for m in used_memories)
    budget -= memory_tokens

    # Cap RAG chunks - trim if needed
    used_rag = rag_chunks[:MAX_RAG_CHUNKS]
    rag_tokens = sum(_estimate(c) for c in used_rag)
    while rag_tokens > budget and len(used_rag) > MIN_RAG_CHUNKS:
        used_rag.pop()
        rag_tokens = sum(_estimate(c) for c in used_rag)
    if rag_tokens > budget:
        used_rag = []
        rag_tokens = 0
    budget -= rag_tokens

    # History trimming
    # If summary exists, replace everything except last SUMMARY_HISTORY_TAIL messages
    effective_history = history
    if conversation_summary and len(history) > SUMMARY_HISTORY_TAIL:
        tail = history[-SUMMARY_HISTORY_TAIL:]
        summary_msg = ChatMessage(role="system", content=f"[Conversation summary]: {conversation_summary}")
        effective_history = [summary_msg] + tail

    # Trim oldest messages until they fit
    trimmed = list(effective_history)
    history_tokens = sum(_msg_tokens(m) for m in trimmed)
    while history_tokens > budget and len(trimmed) > 1:
        trimmed.pop(0)
        history_tokens = sum(_msg_tokens(m) for m in trimmed)

    return trimmed, {
        "context_limit": context_limit,
        "history_tokens": history_tokens,
        "memory_count": len(used_memories),
        "rag_chunks": len(used_rag),
        "budget_remaining": budget - history_tokens,
    }
