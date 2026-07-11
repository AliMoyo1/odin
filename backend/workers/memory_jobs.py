from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone

from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.models import Conversation, Memory, Message, Notification, User
from app.services.events import publish_sync
from app.services.memory_service import suggest
from workers.celery_app import app as celery_app

logger = logging.getLogger(__name__)

_engine = create_async_engine(settings.DATABASE_URL, echo=False)
_sm = async_sessionmaker(_engine, expire_on_commit=False)

_STALE_SUGGESTION_DAYS = 30
_ACTIVE_CAP = 1000
_SUMMARY_MIN_MESSAGES = 50
_SUMMARY_MAX_WORDS = 300
_MAX_EXTRACTION_FACTS = 5
_MAX_FACT_LEN = 500


@celery_app.task(name="extract_memories")
def extract_memories(conversation_id: str) -> None:
    asyncio.run(_async_extract(conversation_id))


@celery_app.task(name="consolidate_memories")
def consolidate_memories() -> None:
    asyncio.run(_async_consolidate())


@celery_app.task(name="summarize_conversations")
def summarize_conversations() -> None:
    asyncio.run(_async_summarize())


async def _async_extract(conversation_id: str) -> None:
    async with _sm() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv is None:
            return
        user_id = conv.user_id

        msgs = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(30)
        )
        recent = list(reversed(msgs.scalars().all()))

    if not recent:
        return

    # Build conversation excerpt for extraction
    lines = []
    for m in recent:
        role = "User" if m.role == "user" else "Hermes"
        content = (m.content or "")[:400]
        if content:
            lines.append(f"{role}: {content}")
    excerpt = "\n".join(lines)

    extraction_prompt = (
        "You are extracting durable user facts from a conversation. "
        "Return ONLY valid JSON in this exact format: "
        '{\"facts\": [{\"value\": \"...\", \"confidence\": \"high\"}]}'
        "\n\nRules:\n"
        "- Maximum 5 facts\n"
        "- Only extract: user preferences, environment details, recurring entities, stated facts about the user\n"
        "- NEVER extract: task content, temporary context, credentials, passwords, API keys, tokens\n"
        "- confidence must be 'high' or 'medium'\n"
        "- value max 500 characters\n"
        "- If no qualifying facts, return {\"facts\": []}\n\n"
        f"Conversation:\n{excerpt}\n\nJSON:"
    )

    response_text = await _llm_call_no_tools(extraction_prompt)
    if not response_text:
        return

    # Strip any markdown fences
    response_text = re.sub(r"```(?:json)?|```", "", response_text).strip()
    # Find the first { ... } block
    match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if not match:
        logger.warning("extract_memories: no JSON found in response for %s", conversation_id)
        return

    try:
        data = json.loads(match.group())
        facts = data.get("facts", [])
    except (json.JSONDecodeError, AttributeError):
        logger.warning("extract_memories: JSON parse failed for %s", conversation_id)
        return

    if not isinstance(facts, list):
        return

    suggested_count = 0
    async with _sm() as session:
        for fact in facts[:_MAX_EXTRACTION_FACTS]:
            if not isinstance(fact, dict):
                continue
            confidence = fact.get("confidence", "")
            value = str(fact.get("value", ""))[:_MAX_FACT_LEN]
            if confidence != "high" or not value:
                continue
            result = await suggest(session, user_id, value, conversation_id)
            if result is not None:
                suggested_count += 1

        if suggested_count > 0:
            n = Notification(
                user_id=user_id,
                title=f"Hermes noticed {suggested_count} thing{'s' if suggested_count != 1 else ''} worth remembering. Review in Knowledge > Memory.",
                category="hermes",
            )
            session.add(n)
            await session.commit()
            await session.refresh(n)
            publish_sync(
                f"events:{user_id}",
                "notification.new",
                {"id": str(n.id), "title": n.title, "body": None, "category": "hermes"},
            )


async def _async_consolidate() -> None:
    async with _sm() as session:
        # Find all users with memories
        result = await session.execute(
            text("SELECT DISTINCT user_id FROM memories WHERE metadata->>'status' = 'active'")
        )
        user_ids = [str(r[0]) for r in result.all()]

    for user_id in user_ids:
        await _consolidate_for_user(user_id)


async def _consolidate_for_user(user_id: str) -> None:
    async with _sm() as session:
        # Delete old suggestions (> 30 days)
        await session.execute(
            text("""
                DELETE FROM memories
                WHERE user_id = :uid
                  AND metadata->>'status' = 'suggested'
                  AND created_at < (now() - interval '30 days')
            """),
            {"uid": user_id},
        )

        # Count active memories
        count_result = await session.execute(
            text("SELECT COUNT(*) FROM memories WHERE user_id = :uid AND metadata->>'status' = 'active'"),
            {"uid": user_id},
        )
        active_count = int(count_result.scalar() or 0)

        stale_result = await session.execute(
            text("""
                SELECT COUNT(*) FROM memories
                WHERE user_id = :uid
                  AND metadata->>'status' = 'active'
                  AND access_count = 0
                  AND created_at < (now() - interval '90 days')
            """),
            {"uid": user_id},
        )
        stale_count = int(stale_result.scalar() or 0)

        if active_count < _ACTIVE_CAP and stale_count == 0:
            await session.commit()
            return

        n = Notification(
            user_id=user_id,
            title=(
                f"Memory review: {active_count} active memories"
                + (f" ({stale_count} unused for 90+ days)" if stale_count else "")
                + (f", {active_count - _ACTIVE_CAP} over the {_ACTIVE_CAP} soft cap" if active_count > _ACTIVE_CAP else "")
                + ". Review in Knowledge > Memory."
            ),
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


async def _async_summarize() -> None:
    import redis

    r = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async with _sm() as session:
        result = await session.execute(
            text("""
                SELECT c.id, c.user_id, c.summary, c.message_count
                FROM conversations c
                WHERE c.message_count >= :min_msgs
                  AND (c.summary IS NULL OR c.message_count > :min_msgs)
            """),
            {"min_msgs": _SUMMARY_MIN_MESSAGES},
        )
        candidates = result.mappings().all()

    for row in candidates:
        conv_id = str(row["id"])
        user_id = str(row["user_id"])
        current_count = int(row["message_count"] or 0)

        # Check if already summarized at this count
        marker_key = f"sumct:{conv_id}"
        last_summary_count = int(r.get(marker_key) or 0)
        if row["summary"] and current_count - last_summary_count < _SUMMARY_MIN_MESSAGES:
            continue

        await _summarize_conversation(conv_id, user_id, r, marker_key)

    r.close()


async def _summarize_conversation(conv_id: str, user_id: str, r, marker_key: str) -> None:
    async with _sm() as session:
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at.asc())
        )
        messages = result.scalars().all()

    if not messages:
        return

    lines = []
    for m in messages:
        role = "User" if m.role == "user" else "Hermes"
        content = (m.content or "")[:300]
        if content:
            lines.append(f"{role}: {content}")

    transcript = "\n".join(lines)
    summary_prompt = (
        f"Summarize this conversation in under {_SUMMARY_MAX_WORDS} words. "
        "Preserve: key decisions made, open questions, named entities (people, tools, projects), "
        "and any facts the user stated. Omit greetings and filler.\n\n"
        f"Conversation:\n{transcript}"
    )

    summary = await _llm_call_no_tools(summary_prompt)
    if not summary:
        return

    async with _sm() as session:
        await session.execute(
            update(Conversation)
            .where(Conversation.id == conv_id)
            .values(summary=summary[:2000])
        )
        await session.commit()

    r.set(marker_key, str(len(messages)))
    logger.info("summarize_conversations: summarized %s (%d messages)", conv_id, len(messages))


async def _llm_call_no_tools(prompt: str) -> str:
    """Single-shot LLM call with no tools. Returns the text response."""
    from app.hermes.router import stream_with_failover
    from app.hermes.types import ChatMessage, TextDelta, TurnDone

    messages = [ChatMessage(role="user", content=prompt)]
    text_parts: list[str] = []

    try:
        async for event in stream_with_failover("You are a helpful assistant.", messages, tools=[]):
            if isinstance(event, TextDelta):
                text_parts.append(event.text)
            elif isinstance(event, TurnDone):
                break
    except Exception as exc:
        logger.error("_llm_call_no_tools failed: %s", exc)
        return ""

    return "".join(text_parts)
