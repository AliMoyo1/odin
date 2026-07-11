from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel

from app.hermes.tools.registry import registry
from app.services.file_service import resolve_in_workspace

_MAX_READ_BYTES = 20000


class ListFilesInput(BaseModel):
    path: str = ""


class ReadFileInput(BaseModel):
    path: str
    max_bytes: int = _MAX_READ_BYTES


class WriteFileInput(BaseModel):
    path: str
    content: str


class DeleteFileInput(BaseModel):
    path: str


async def _list_files(inputs: ListFilesInput, session=None, user_id: str | None = None) -> str:
    try:
        target = resolve_in_workspace(inputs.path)
    except ValueError:
        return json.dumps({"ok": False, "error": "path outside workspace"})

    if not target.exists():
        return json.dumps({"ok": False, "error": "path does not exist"})

    if target.is_file():
        return json.dumps({"ok": True, "entries": [{"name": target.name, "path": inputs.path, "type": "file"}]})

    from app.services.file_service import workspace_root, should_skip
    entries = []
    for item in sorted(target.iterdir()):
        if should_skip(item.name):
            continue
        rel = str(item.relative_to(workspace_root()))
        entries.append({
            "name": item.name,
            "path": rel,
            "type": "dir" if item.is_dir() else "file",
        })
    return json.dumps({"ok": True, "entries": entries})


async def _read_file(inputs: ReadFileInput, session=None, user_id: str | None = None) -> str:
    try:
        target = resolve_in_workspace(inputs.path)
    except ValueError:
        return json.dumps({"ok": False, "error": "path outside workspace"})

    if not target.is_file():
        return json.dumps({"ok": False, "error": "not a file"})

    max_bytes = min(inputs.max_bytes, _MAX_READ_BYTES)
    try:
        with target.open("r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_bytes)
        truncated = target.stat().st_size > max_bytes
        return json.dumps({"ok": True, "content": content, "truncated": truncated})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


async def _write_file(inputs: WriteFileInput, session=None, user_id: str | None = None) -> str:
    try:
        target = resolve_in_workspace(inputs.path)
    except ValueError:
        return json.dumps({"ok": False, "error": "path outside workspace"})

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(inputs.content, encoding="utf-8")
        return json.dumps({"ok": True, "path": inputs.path, "bytes_written": len(inputs.content.encode())})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


async def _delete_file(inputs: DeleteFileInput, session=None, user_id: str | None = None) -> str:
    try:
        target = resolve_in_workspace(inputs.path)
    except ValueError:
        return json.dumps({"ok": False, "error": "path outside workspace"})

    if not target.is_file():
        return json.dumps({"ok": False, "error": "not a file"})

    from app.services.file_service import trash_path
    dest = trash_path(target.name)
    os.replace(str(target), str(dest))
    return json.dumps({"ok": True, "moved_to_trash": str(dest.name)})


registry.register("list_files", "List files in the workspace directory", ListFilesInput, _list_files)
registry.register("read_file", "Read a file from the workspace", ReadFileInput, _read_file)
registry.register("write_file", "Write content to a file in the workspace", WriteFileInput, _write_file, requires_approval=True)
registry.register("delete_file", "Move a file to trash (recoverable)", DeleteFileInput, _delete_file, requires_approval=True)
