from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class NotificationCategory(StrEnum):
    task = "task"
    system = "system"
    hermes = "hermes"
    whatsapp = "whatsapp"


class NotificationOut(BaseModel):
    id: str
    user_id: str
    title: str
    body: str | None
    category: str
    read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityOut(BaseModel):
    id: str
    user_id: str
    action: str
    resource_type: str | None
    resource_id: str | None
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
