from datetime import datetime

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    workspace_path: str | None = None


class ProjectPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    workspace_path: str | None = None


class ProjectOut(BaseModel):
    id: str
    user_id: str
    name: str
    description: str | None
    workspace_path: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
