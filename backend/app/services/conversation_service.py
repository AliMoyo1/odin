from fastapi import HTTPException
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Conversation, Message
from app.schemas.conversations import ConversationCreate, ConversationPatch


async def create_conversation(
    session: AsyncSession, user_id: str, body: ConversationCreate
) -> Conversation:
    conv = Conversation(
        user_id=user_id,
        project_id=body.project_id,
        title=body.title or "New Conversation",
    )
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv


async def list_conversations(
    session: AsyncSession,
    user_id: str,
    project_id: str | None = None,
    archived: bool = False,
) -> list[Conversation]:
    q = select(Conversation).where(Conversation.user_id == user_id)
    if project_id:
        q = q.where(Conversation.project_id == project_id)
    q = q.order_by(Conversation.updated_at.desc())
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_conversation(session: AsyncSession, user_id: str, conv_id: str) -> Conversation:
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conv_id, Conversation.user_id == user_id
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return conv


async def patch_conversation(
    session: AsyncSession, user_id: str, conv_id: str, body: ConversationPatch
) -> Conversation:
    conv = await get_conversation(session, user_id, conv_id)
    if body.title is not None:
        conv.title = body.title
    if body.project_id is not None:
        conv.project_id = body.project_id
    await session.commit()
    await session.refresh(conv)
    return conv


async def get_messages(
    session: AsyncSession,
    user_id: str,
    conv_id: str,
    limit: int = 50,
    before: str | None = None,
) -> list[Message]:
    await get_conversation(session, user_id, conv_id)
    q = select(Message).where(Message.conversation_id == conv_id)
    if before:
        ref = await session.execute(select(Message).where(Message.id == before))
        ref_msg = ref.scalar_one_or_none()
        if ref_msg:
            q = q.where(Message.created_at < ref_msg.created_at)
    q = q.order_by(Message.created_at.desc()).limit(limit)
    result = await session.execute(q)
    msgs = list(result.scalars().all())
    msgs.reverse()
    return msgs


async def append_message(
    session: AsyncSession,
    conversation_id: str,
    role: str,
    content: str | None,
    metadata: dict | None = None,
    token_count: int | None = None,
) -> Message:
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        token_count=token_count,
        extra_meta=metadata,
    )
    session.add(msg)
    await session.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(
            message_count=Conversation.message_count + 1,
            updated_at=text("CURRENT_TIMESTAMP"),
        )
    )
    await session.commit()
    await session.refresh(msg)
    return msg


async def search_messages(
    session: AsyncSession, user_id: str, q: str, limit: int = 20
) -> list[dict]:
    sql = text("""
        SELECT m.id, m.conversation_id, c.title as conv_title, m.role,
               m.content, m.created_at,
               ts_rank(to_tsvector('english', m.content), plainto_tsquery('english', :q)) as rank
        FROM messages m
        JOIN conversations c ON c.id = m.conversation_id
        WHERE c.user_id = :uid
          AND m.content IS NOT NULL
          AND to_tsvector('english', m.content) @@ plainto_tsquery('english', :q)
        ORDER BY rank DESC
        LIMIT :limit
    """)
    result = await session.execute(sql, {"uid": user_id, "q": q, "limit": limit})
    rows = result.fetchall()
    return [
        {
            "message_id": str(r.id),
            "conversation_id": str(r.conversation_id),
            "conversation_title": r.conv_title,
            "role": r.role,
            "snippet": (r.content or "")[:200],
            "created_at": r.created_at,
        }
        for r in rows
    ]
