from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

import redis.asyncio as aioredis
import structlog

from app.config import settings
from app.db import async_session
from app.hermes import gate as _gate
from app.hermes import router as _router
from app.hermes.budget import build_budgeted_messages
from app.hermes.prompt import build_system_prompt
from app.hermes.tools import file_tools, kb_tools, memory_tools, task_tools  # noqa: registers tools
from app.hermes.tools.registry import registry as tool_registry
from app.hermes.types import ChatMessage, TextDelta, ToolCall, ToolCallReady, TurnDone
from app.services import conversation_service
from app.services.events import publish

logger = structlog.get_logger(service="loop")

_MAX_ITERATIONS = 8
_TOKEN_FLUSH_INTERVAL = 0.05  # seconds


async def _publish_event(channel: str, event_type: str, data: dict) -> None:
    try:
        await publish(channel, event_type, data)
    except Exception:
        pass


async def _has_auto_approval(user_id: str, tool_name: str, project_id: str | None) -> bool:
    from sqlalchemy import select, text as sqla_text
    async with async_session() as session:
        sql = sqla_text("""
            SELECT id FROM tool_approvals
            WHERE user_id = :uid AND tool_name = :tn
              AND auto_approve = TRUE
              AND (project_id = :pid OR (project_id IS NULL AND :pid IS NULL))
        """)
        result = await session.execute(sql, {"uid": user_id, "tn": tool_name, "pid": project_id})
        return result.fetchone() is not None


async def _register_run(run_id: str, conversation_id: str) -> None:
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await r.hset("runs:active", run_id, json.dumps({
            "conversation_id": conversation_id,
            "started_at": time.time(),
        }))
    finally:
        await r.aclose()


async def _unregister_run(run_id: str) -> None:
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await r.hdel("runs:active", run_id)
    finally:
        await r.aclose()


def _messages_to_serializable(messages: list[ChatMessage]) -> list[dict]:
    return [
        {
            "role": m.role,
            "content": m.content,
            "tool_call_id": m.tool_call_id,
            "tool_calls": [
                {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                for tc in (m.tool_calls or [])
            ] if m.tool_calls else None,
            "metadata": m.metadata,
        }
        for m in messages
    ]


async def run_turn(
    user_id: str,
    conversation_id: str,
    user_message_id: str,
    project_id: str | None = None,
) -> None:
    run_id = str(uuid.uuid4())
    channel = f"events:{user_id}"

    await _register_run(run_id, conversation_id)
    partial_text = ""

    try:
        conv_summary: str | None = None
        recalled_memories: list[str] = []
        latest_user_text: str = ""

        async with async_session() as session:
            raw_history = await conversation_service.get_messages(session, user_id, conversation_id, limit=100)
            try:
                conv = await conversation_service.get_conversation(session, user_id, conversation_id)
                conv_summary = conv.summary
            except Exception:
                pass

        # Latest user message for recall
        for m in reversed(raw_history):
            if m.role == "user" and m.content:
                latest_user_text = m.content
                break

        if latest_user_text:
            try:
                async with async_session() as session:
                    from app.services.memory_service import recall as _recall
                    results = await _recall(session, user_id, latest_user_text, k=5)
                    recalled_memories = [r.formatted for r in results]
            except Exception:
                pass

        history = [
            ChatMessage(
                role=m.role,
                content=m.content,
                metadata=m.extra_meta or {},
            )
            for m in raw_history
        ]

        system = build_system_prompt(
            user_email=user_id,
            memories=recalled_memories if recalled_memories else None,
        )
        budgeted, budget_info = build_budgeted_messages(
            system, history, recalled_memories, [],
            conversation_summary=conv_summary,
        )
        tools = tool_registry.specs()
        iteration = 0
        last_tool_call: tuple[str, str] | None = None  # (name, args_hash) for repeat guard

        while iteration < _MAX_ITERATIONS:
            iteration += 1
            accumulated_text = ""
            tool_calls_this_turn: list[ToolCall] = []
            raw_content = None

            token_buffer: list[str] = []
            last_flush = asyncio.get_event_loop().time()

            async def flush_tokens() -> None:
                nonlocal last_flush
                if token_buffer:
                    await _publish_event(channel, "message.token", {"text": "".join(token_buffer)})
                    token_buffer.clear()
                    last_flush = asyncio.get_event_loop().time()

            try:
                async for event in _router.stream_with_failover(system, budgeted, tools):
                    if isinstance(event, TextDelta):
                        accumulated_text += event.text
                        token_buffer.append(event.text)
                        if asyncio.get_event_loop().time() - last_flush >= _TOKEN_FLUSH_INTERVAL:
                            await flush_tokens()

                    elif isinstance(event, ToolCallReady):
                        await flush_tokens()
                        tool_calls_this_turn.append(event.call)

                    elif isinstance(event, TurnDone):
                        await flush_tokens()
                        raw_content = event.raw_content
                        if event.stop_reason == "error":
                            await _publish_event(channel, "error", {"message": "Provider error during generation"})
                            return

            except asyncio.CancelledError:
                await flush_tokens()
                if accumulated_text:
                    async with async_session() as session:
                        await conversation_service.append_message(
                            session, conversation_id, "assistant", accumulated_text,
                            metadata={"partial": True},
                        )
                await _publish_event(channel, "message.done", {"partial": True})
                raise

            # Persist assistant message
            assistant_content = raw_content if raw_content else (accumulated_text or None)
            async with async_session() as session:
                asst_msg = await conversation_service.append_message(
                    session, conversation_id, "assistant", accumulated_text or None,
                    metadata={"raw_content": raw_content or []},
                )

            # Add to budgeted messages for next turn
            budgeted.append(ChatMessage(
                role="assistant",
                content=raw_content if raw_content else (accumulated_text or ""),
                tool_calls=tool_calls_this_turn if tool_calls_this_turn else None,
                metadata={"provider": "unknown"},
            ))

            if not tool_calls_this_turn:
                await _publish_event(channel, "message.done", {"message_id": str(asst_msg.id)})
                await _maybe_enqueue_extraction(conversation_id, len(raw_history) + 1)
                return

            # Process tool calls
            for call in tool_calls_this_turn:
                spec = tool_registry.get_spec(call.name)
                args_hash = json.dumps(call.arguments, sort_keys=True)

                # Repeated-call guard
                if last_tool_call == (call.name, args_hash):
                    result_text = json.dumps({"ok": False, "message": "Duplicate call skipped; using previous result."})
                    budgeted.append(ChatMessage(
                        role="tool_result",
                        content=result_text,
                        tool_call_id=call.id,
                        metadata={"tool_name": call.name},
                    ))
                    continue

                last_tool_call = (call.name, args_hash)

                # Check approval
                if spec and spec.requires_approval:
                    auto = await _has_auto_approval(user_id, call.name, project_id)
                    if not auto:
                        approval_id, expires_in = await _gate.create_gate(
                            conversation_id=conversation_id,
                            user_id=user_id,
                            project_id=project_id,
                            call=call,
                            provider_messages_snapshot=_messages_to_serializable(budgeted),
                        )
                        async with async_session() as session:
                            await conversation_service.append_message(
                                session, conversation_id, "system",
                                f"Awaiting approval for {call.name}",
                                metadata={"approval_id": approval_id},
                            )
                        await _publish_event(channel, "gate.locked", {
                            "approval_id": approval_id,
                            "tool": call.name,
                            "args_preview": str(call.arguments)[:100],
                            "expires_in": expires_in,
                        })
                        return

                await _publish_event(channel, "tool.start", {"tool": call.name, "args": call.arguments})
                async with async_session() as session:
                    result_text = await tool_registry.dispatch(call, db_session=session, user_id=user_id)

                await _publish_event(channel, "tool.result", {"tool": call.name, "result": result_text[:500]})
                budgeted.append(ChatMessage(
                    role="tool_result",
                    content=result_text,
                    tool_call_id=call.id,
                    metadata={"tool_name": call.name},
                ))

        # Iteration cap hit
        budgeted.append(ChatMessage(
            role="system",
            content="Iteration budget exhausted. Summarize what you have accomplished so far.",
        ))
        async for event in _router.stream_with_failover(system, budgeted, []):
            if isinstance(event, TextDelta):
                accumulated_text += event.text
                await _publish_event(channel, "message.token", {"text": event.text})
            elif isinstance(event, TurnDone):
                break

        if accumulated_text:
            async with async_session() as session:
                asst_msg = await conversation_service.append_message(
                    session, conversation_id, "assistant", accumulated_text,
                )
        await _publish_event(channel, "message.done", {})

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error("loop_error", error=str(e), conversation_id=conversation_id)
        await _publish_event(channel, "error", {"message": "Internal error during generation"})
    finally:
        await _unregister_run(run_id)


_EXTRACTION_CADENCE = 10  # messages between extractions


async def _maybe_enqueue_extraction(conversation_id: str, current_message_count: int) -> None:
    """Enqueue memory extraction if the conversation has grown by CADENCE messages since last extraction."""
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        marker_key = f"memext:{conversation_id}"
        marker = await r.get(marker_key)
        last_count = int(marker) if marker else 0
        if current_message_count - last_count >= _EXTRACTION_CADENCE:
            await r.set(marker_key, str(current_message_count))
            from workers.memory_jobs import extract_memories
            extract_memories.delay(conversation_id)
    except Exception:
        pass
    finally:
        await r.aclose()


async def resume_from_gate(approval_data: dict, result_text: str) -> None:
    """Resume a turn after a gate approval or denial."""
    conversation_id = approval_data["conversation_id"]
    user_id = approval_data["user_id"]
    project_id = approval_data.get("project_id")
    tc_data = approval_data["tool_call"]
    call = ToolCall(id=tc_data["id"], name=tc_data["name"], arguments=tc_data["arguments"])
    snapshot = approval_data.get("messages_snapshot", [])

    def _restore(raw: list) -> list[ChatMessage]:
        msgs = []
        for m in raw:
            tool_calls = None
            if m.get("tool_calls"):
                tool_calls = [ToolCall(id=t["id"], name=t["name"], arguments=t["arguments"]) for t in m["tool_calls"]]
            msgs.append(ChatMessage(
                role=m["role"],
                content=m["content"],
                tool_call_id=m.get("tool_call_id"),
                tool_calls=tool_calls,
                metadata=m.get("metadata") or {},
            ))
        return msgs

    budgeted = _restore(snapshot)
    budgeted.append(ChatMessage(
        role="tool_result",
        content=result_text,
        tool_call_id=call.id,
        metadata={"tool_name": call.name},
    ))

    system = build_system_prompt(user_email=user_id)
    tools = tool_registry.specs()
    channel = f"events:{user_id}"

    run_id = str(uuid.uuid4())
    await _register_run(run_id, conversation_id)

    try:
        accumulated_text = ""
        async for event in _router.stream_with_failover(system, budgeted, tools):
            if isinstance(event, TextDelta):
                accumulated_text += event.text
                await _publish_event(channel, "message.token", {"text": event.text})
            elif isinstance(event, TurnDone):
                break

        if accumulated_text:
            async with async_session() as session:
                asst_msg = await conversation_service.append_message(
                    session, conversation_id, "assistant", accumulated_text,
                )
            await _publish_event(channel, "message.done", {"message_id": str(asst_msg.id)})
        else:
            await _publish_event(channel, "message.done", {})
    finally:
        await _unregister_run(run_id)
