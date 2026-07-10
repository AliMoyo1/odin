# PLAN-05: File Service, Knowledge Base, RAG Pipeline, Workspace Watcher

Goal: the sandboxed filesystem service (browse, upload, download), the ingestion pipeline (extract, chunk with per-type config, embed, index in pgvector with citations), semantic search with optional cross-encoder rerank, the real `search_knowledge` and file tools for Hermes, and the watchdog daemon with Syncthing conflict handling.

Prerequisites: PLAN-04. Spec references: SPEC 2.5 (FILE/KB), 6.4, 6.5, Doc 11, Doc 15.

## Files to create or touch

```
backend\app\services\file_service.py
backend\app\services\extract.py
backend\app\services\chunker.py
backend\app\services\embeddings.py
backend\app\services\kb_search.py
backend\app\services\rerank.py
backend\app\routers\files.py
backend\app\routers\kb.py
backend\workers\indexing.py
backend\app\watcher\__init__.py
backend\app\watcher\daemon.py
backend\app\hermes\tools\file_tools.py   (replace internals)
backend\app\hermes\tools\kb_tools.py     (replace stub)
backend\tests\test_sandbox.py  test_chunker.py  test_kb.py
docker-compose.dev.yml                   (add watcher service)
```

## Steps in order

### Step 1: the sandbox primitive (used by everything)

In `file_service.py`:

```python
from pathlib import Path
from app.config import settings

def resolve_in_workspace(relative: str) -> Path:
    root = Path(settings.WORKSPACE_ROOT).resolve()
    candidate = (root / relative).resolve()
    candidate.relative_to(root)   # raises ValueError if outside
    return candidate
```

Every read, write, list, delete, download, upload, and watcher callback goes through this function. Reject absolute input paths and any input containing a null byte before resolving. This replaces the `startswith` sketch in SPEC 11.2 (see PLAN-00 delta 4).

### Step 2: file service and router (FILE-01..03)

- `GET /api/v1/files/tree?path=`: one directory level per call (name, is_dir, size, mtime), sorted dirs-first. Skip `.stversions` and `.sync-conflict-*` entries.
- `GET /api/v1/files/download?path=`: `FileResponse` with `content-disposition` attachment; sandbox-resolved.
- `POST /api/v1/files/upload` multipart with `path` form field (target directory): enforce the allowlist `pdf docx txt md html csv json py js ts yaml yml xml png jpg jpeg` on the LOWERCASED extension, stream to a temp file in the same directory counting bytes, abort and delete at 50 MB regardless of Content-Length, then atomic `os.replace` to the final name. Name collisions get ` (1)` suffixes, never overwrite.
- `DELETE /api/v1/files?path=`: moves the file into `WORKSPACE_ROOT/.trash/` with a timestamp prefix instead of unlinking (cheap undo; Hermes' delete goes through the approval gate anyway).
- After any mutation, write an activity_log row and enqueue indexing if the extension is a KB type.
- Chat uploads (CHAT-05): the chat upload endpoint saves into the active project's directory (or `Inbox/` when no project) via the same service, then appends a system message with the relative path link.

### Step 3: extraction (KB-01)

`extract.py` returns `list[ExtractedBlock(text, page_number: int or None, section_ref: str or None)]`:

- pdf: pdfplumber, one block per page with `page_number`. If total extracted text is under 50 characters, mark the document processed with `metadata.warning = "no extractable text (scanned?)"` and skip embedding; do not fail the task.
- docx: python-docx paragraphs, blocks split on Heading styles, `section_ref` = latest heading text.
- md: split on headings, `section_ref` = heading.
- html: BeautifulSoup, remove `script` and `style`, `get_text(separator="\n")`.
- txt, csv, json, py, js, ts, yaml, yml, xml: raw text single block. Images (png, jpg, jpeg) are stored but NEVER indexed.

### Step 4: chunker with per-type config (KB-02, SPEC 15.1)

Token counting with tiktoken `cl100k_base`. Config resolution: legal-ish PDFs and any file whose `knowledge_documents.chunk_config` says so use 1500/300; code extensions (py, js, ts) 500/100; default 1000/200. Store the resolved config on the document row at ingestion time. Recursive split: paragraphs, then sentences, then hard token windows, always with the configured overlap. Every chunk records `chunk_index`, inherited `page_number` and `section_ref`.

### Step 5: embeddings.py (configurable, SPEC 8.1)

- Read the active `embedding_config` row once per task run. Provider `openai`: `client.embeddings.create(model=..., input=batch)` with batches of at most 100 texts, exponential backoff on 429/5xx (3 retries).
- GUARD: `len(vector) == config.dimensions` before any insert; mismatch aborts the task with a clear error (protects against model/dimension drift).
- Insert chunks with pgvector: register the asyncpg codec once (`pgvector.asyncpg.register_vector`) via the engine's connect event, so Python lists bind natively.
- If OPENAI_API_KEY is blank: documents stay `processed=FALSE` with a notification "Knowledge indexing disabled: no embedding key" once (not per file).

### Step 6: the Celery indexing task (idempotent)

`workers\indexing.py :: index_document(document_id)`:

1. Load document, resolve file in sandbox, compute sha256 of content. If it equals `content_sha256` and `processed=TRUE`, exit (no-op).
2. Extract, chunk, embed.
3. In ONE transaction: `DELETE FROM knowledge_chunks WHERE document_id = :id`, insert all new chunks, update the document `processed=TRUE, indexed_at=now, content_sha256=..., embedding_config_id=active`.
4. Publish `notification.new` "Indexed {filename}: N chunks" via `publish_sync`.

`POST /api/v1/kb/documents` (register an uploaded file for indexing), `POST /api/v1/kb/notes` (KB-03: markdown note saved to `Knowledge/notes/{slug}.md` then indexed), `GET /api/v1/kb/documents` (status list), `POST /api/v1/kb/search` (test UI: returns ranked chunks with scores and citations).

### Step 7: search and rerank (KB-05, SPEC 15.2)

`kb_search.py :: search(user_id, query, project_id=None, k=5)`:

1. Embed the query with the SAME active model.
2. `SELECT ..., embedding <=> :qvec AS distance FROM knowledge_chunks JOIN knowledge_documents ... WHERE user_id = :uid ORDER BY embedding <=> :qvec LIMIT 10` (optionally filter project).
3. If `settings.RERANK_ENABLED`: pass the 10 through `rerank.py` (lazy-loaded `sentence-transformers` CrossEncoder `cross-encoder/ms-marco-MiniLM-L-6-v2`, loaded once per process, only importable when requirements-rerank.txt is installed) and keep the top 5 by rerank score. Else keep the top 5 by distance.
4. Return chunks with `citation = f"[Source: {filename}, p.{page_number}]"` (or section_ref when no page).

Replace the Hermes `search_knowledge` stub: returns the formatted chunks; prompt.py already instructs citation.

### Step 8: watcher daemon (KB-04, SPEC 11.2, 11.3)

`watcher\daemon.py`, run as its own compose service (same image, command `python -m app.watcher.daemon`):

- Use `PollingObserver` when `WATCHER_FORCE_POLLING=1` (required on Windows bind mounts), else inotify `Observer`.
- Debounce: collect events per path, act 2 seconds after the last event for that path.
- Ignore: directories, `.trash/`, `.stversions/`, names starting with `~$` or ending `.tmp` or `.part`.
- `.sync-conflict-` in the name: do NOT index; write an activity_log row and `notification.new` "File conflict detected: {name}. Review in the file browser." (SPEC 11.3).
- Otherwise, if the extension is a KB type: upsert the `knowledge_documents` row by (user, relative path) and enqueue `index_document` via `celery_app.send_task`.
- Deletions: mark the document row `processed=FALSE` with `metadata.deleted=true` and delete its chunks.

Add the service to docker-compose.dev.yml with the same mounts as celery-worker.

### Step 9: tests

- `test_sandbox.py`: `../../etc/passwd` raises; absolute path raises; `Projects/../Inbox/x.txt` resolves INSIDE and is allowed; sibling-prefix trap `WORKSPACE_ROOT + "2"` is rejected.
- `test_chunker.py`: overlap continuity (last N tokens of chunk i appear in chunk i+1), code file uses 500/100, page numbers survive chunking.
- `test_kb.py`: end-to-end with a small txt fixture and a fake embedding function (monkeypatched, deterministic vectors): index, search returns the seeded chunk first, re-index after content change replaces chunks (old chunk ids gone).

## Edge cases a weaker model would miss

1. **`startswith` sandbox checks are bypassable** (`/data/ODIN2` passes a `/data/ODIN` prefix check; on Windows also case and separator games). `resolve()` + `relative_to()` only. Test 1 encodes this.
2. **Symlinks:** `resolve()` follows them; a symlink inside the workspace pointing outside will fail `relative_to`, which is exactly the desired behavior. Do not "fix" it by checking the unresolved path.
3. **Trust neither Content-Length nor the extension alone.** Count streamed bytes yourself; a lying header otherwise writes 2 GB to disk. Lowercase the extension before the allowlist check.
4. **Scanned PDFs extract nothing.** Mark with a warning and move on; failing the task means the queue retries a hopeless job forever.
5. **Re-indexing must delete old chunks in the same transaction as inserting new ones**, or a crash mid-way leaves the doc half-duplicated in search results.
6. **Dimension drift guard (Step 5) is load-bearing.** Changing `embedding_config` to a 768-dim model without migrating the `VECTOR(1536)` column must fail loudly at index time, not corrupt inserts.
7. **inotify does not fire on Windows Docker bind mounts.** Dev must run the PollingObserver (`WATCHER_FORCE_POLLING=1` is already in `.env.example`); production Linux flips it to 0 for real inotify.
8. **Debounce or die:** editors and Syncthing emit bursts of events per save; without the 2-second settle you enqueue five index jobs per keystroke-save.
9. **The rerank import must be lazy and optional.** `import sentence_transformers` at module top level makes the whole API require torch. Import inside the function, guarded by the env flag.
10. **`<=>` is cosine DISTANCE (lower is better) and only uses the HNSW index when the query vector is bound with the pgvector codec.** Passing a Python list as a string parameter silently falls back to a sequential scan.
11. **Uploads must be atomic** (temp file + `os.replace`), or the watcher indexes half-written files.
12. **Never index `.trash/`** or deleted files keep resurfacing in RAG answers.

## Acceptance criteria (verify each)

1. `pytest tests/test_sandbox.py tests/test_chunker.py tests/test_kb.py -q` passes.
2. Upload a real PDF via curl: document row appears, `processed=TRUE`, chunks have page numbers; `POST /api/v1/kb/search` for a phrase from page 2 returns a chunk citing p.2.
3. Ask Hermes a question answerable only from that PDF: the streamed answer includes `[Source: <filename>, p.N]`.
4. Upload a 51 MB file: 413-style rejection, no partial file remains in the target directory.
5. Upload `evil.exe`: rejected by the allowlist.
6. Edit a text file directly in `workspace\Knowledge\` on the Windows host: within ~10 seconds the watcher enqueues, the document re-indexes, `indexed_at` updates.
7. Create a file named `report.sync-conflict-20260710-1200.md` in the workspace: a conflict notification appears, and it is NOT in `knowledge_documents`.
8. With `RERANK_ENABLED=0` everything above works without torch installed.
