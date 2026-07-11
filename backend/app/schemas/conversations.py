from datetime import datetime

from pydantic import BaseModel


class ConversationCreate(BaseModel):
    title: str | None = None
    project_id: str | None = None


class ConversationPatch(BaseModel):
    title: str | None = None
    project_id: str | None = None
    archived: bool | None = None


class ConversationOut(BaseModel):
    id: str
    user_id: str
    project_id: str | None
    title: str | None
    summary: str | None
    message_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    role: str
    content: str | None = None
    token_count: int | None = None


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str | None
    content_blocks: list | None
    token_count: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageSearchResult(BaseModel):
    message_id: str
    conversation_id: str
    conversation_title: str | None
    role: str
    snippet: str
    created_at: datetime
