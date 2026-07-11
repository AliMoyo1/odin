from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import delete as sa_delete, select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models.models import KnowledgeChunk, KnowledgeDocument, User
from app.services.file_service import (
    is_allowed_upload,
    is_kb_type,
    is_sync_conflict,
    log_file_activity,
    resolve_in_workspace,
    should_skip,
    trash_path,
    workspace_root,
)

router = APIRouter(prefix="/api/v1/files", tags=["files"])

_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
_READ_CHUNK = 65536


class FileEntry(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: int | None
    mtime: float | None


class FileTreeOut(BaseModel):
    entries: list[FileEntry]


class UploadOut(BaseModel):
    path: str
    size: int


@router.get("/tree", response_model=FileTreeOut)
async def file_tree(
    path: str = Query(""),
    user: User = Depends(get_current_user),
):
    try:
        target = resolve_in_workspace(path)
    except ValueError:
        raise HTTPException(400, "Invalid path")

    if not target.exists():
        raise HTTPException(404, "Path not found")

    if target.is_file():
        stat = target.stat()
        rel = str(target.relative_to(workspace_root()))
        return FileTreeOut(entries=[FileEntry(
            name=target.name, path=rel, is_dir=False,
            size=stat.st_size, mtime=stat.st_mtime,
        )])

    entries: list[FileEntry] = []
    for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if should_skip(item.name):
            continue
        stat = item.stat() if item.is_file() else None
        rel = str(item.relative_to(workspace_root()))
        entries.append(FileEntry(
            name=item.name, path=rel, is_dir=item.is_dir(),
            size=stat.st_size if stat else None,
            mtime=stat.st_mtime if stat else None,
        ))

    return FileTreeOut(entries=entries)


@router.get("/download")
async def download_file(
    path: str = Query(...),
    user: User = Depends(get_current_user),
):
    try:
        target = resolve_in_workspace(path)
    except ValueError:
        raise HTTPException(400, "Invalid path")

    if not target.exists() or not target.is_file():
        raise HTTPException(404, "File not found")

    return FileResponse(
        str(target),
        filename=target.name,
        headers={"Content-Disposition": f'attachment; filename="{target.name}"'},
    )


@router.post("/upload", response_model=UploadOut, status_code=201)
async def upload_file(
    path: str = Query(""),
    file: UploadFile = ...,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower().lstrip(".")
    if not is_allowed_upload(ext):
        raise HTTPException(415, f"File type '.{ext}' not allowed")

    try:
        target_dir = resolve_in_workspace(path)
    except ValueError:
        raise HTTPException(400, "Invalid path")

    if not target_dir.exists():
        raise HTTPException(404, "Target directory not found")
    if target_dir.is_file():
        target_dir = target_dir.parent

    # Determine unique filename
    base = Path(filename)
    final_path = target_dir / base.name
    counter = 1
    while final_path.exists():
        final_path = target_dir / f"{base.stem} ({counter}){base.suffix}"
        counter += 1

    # Stream to temp file, count bytes to enforce limit
    fd, tmp_path = tempfile.mkstemp(dir=str(target_dir), prefix=".upload_")
    too_large = False
    total = 0
    try:
        with os.fdopen(fd, "wb") as f:
            while True:
                chunk = await file.read(_READ_CHUNK)
                if not chunk:
                    break
                total += len(chunk)
                if total > _MAX_UPLOAD_BYTES:
                    too_large = True
                    break
                f.write(chunk)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    if too_large:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise HTTPException(413, "File exceeds 50 MB limit")

    # Atomic rename
    os.replace(tmp_path, str(final_path))

    rel_path = str(final_path.relative_to(workspace_root()))
    await log_file_activity(session, user.id, "file.upload", rel_path)

    doc_id: str | None = None
    if is_kb_type(ext) and not is_sync_conflict(final_path.name):
        result = await session.execute(
            sa_select(KnowledgeDocument).where(
                KnowledgeDocument.user_id == user.id,
                KnowledgeDocument.file_path == rel_path,
            )
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            doc = KnowledgeDocument(
                user_id=user.id,
                file_path=rel_path,
                file_name=final_path.name,
                file_size=total,
            )
            session.add(doc)
            await session.flush()
        doc_id = doc.id

    await session.commit()

    if doc_id:
        from workers.indexing import index_document
        index_document.delay(doc_id)

    return UploadOut(path=rel_path, size=total)


@router.delete("")
async def delete_file(
    path: str = Query(...),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    try:
        target = resolve_in_workspace(path)
    except ValueError:
        raise HTTPException(400, "Invalid path")

    if not target.exists() or not target.is_file():
        raise HTTPException(404, "File not found")

    dest = trash_path(target.name)
    os.replace(str(target), str(dest))

    await log_file_activity(session, user.id, "file.delete", path)

    result = await session.execute(
        sa_select(KnowledgeDocument).where(
            KnowledgeDocument.user_id == user.id,
            KnowledgeDocument.file_path == path,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is not None:
        await session.execute(
            sa_delete(KnowledgeChunk).where(KnowledgeChunk.document_id == doc.id)
        )
        doc.processed = False
        doc.extra_meta = {**(doc.extra_meta or {}), "deleted": True}

    await session.commit()
    return {"moved_to_trash": True}
