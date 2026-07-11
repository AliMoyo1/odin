# PLAN-05 Execution Log

## Status: COMPLETE

## Steps

- [x] Step 1: sandbox primitive (resolve_in_workspace)
- [x] Step 2: file service and router (FILE-01..03)
- [x] Step 3: extract.py (KB-01)
- [x] Step 4: chunker with per-type config (KB-02)
- [x] Step 5: embeddings.py (configurable, SPEC 8.1)
- [x] Step 6: Celery indexing task (idempotent, one transaction)
- [x] Step 7: kb_search.py + rerank.py (KB-05, SPEC 15.2)
- [x] Step 8: watcher daemon (KB-04, PollingObserver, debounce, conflict handling)
- [x] Step 9: tests (test_sandbox.py, test_chunker.py, test_kb.py)

## Changes made

- Created plans/PLAN-05-execution-log.md
- Created alembic/versions/0002_knowledge_chunks_section_ref.py (adds section_ref + embedding_config_id)
- Updated app/models/models.py (section_ref on KnowledgeChunk, embedding_config_id on KnowledgeDocument)
- Created app/services/file_service.py (resolve_in_workspace sandbox, KB_EXTENSIONS, allowlist, trash, activity log)
- Created app/services/extract.py (pdf/docx/md/html/raw extraction, ExtractedBlock dataclass)
- Created app/services/chunker.py (tiktoken cl100k_base, per-type config 500/100 code, 1000/200 default, hard split with overlap)
- Created app/services/embeddings.py (OpenAI async, batches of 100, retry 429/5xx, dimension guard)
- Created app/services/kb_search.py (embed query, HNSW cosine via CAST, optional rerank, citations)
- Created app/services/rerank.py (lazy CrossEncoder import, cross-encoder/ms-marco-MiniLM-L-6-v2)
- Created workers/indexing.py (idempotent sha256 check, one-transaction delete+insert+update, post-commit notification)
- Created app/routers/files.py (tree, download, upload with 50MB streaming + allowlist, delete to trash)
- Created app/routers/kb.py (register document, create note, list documents, semantic search endpoint)
- Updated app/hermes/tools/file_tools.py (uses resolve_in_workspace, adds delete_file tool)
- Updated app/hermes/tools/kb_tools.py (replaces stub: calls kb_search.search with session+user_id)
- Created app/watcher/__init__.py
- Created app/watcher/daemon.py (PollingObserver/inotify, 2s debounce, conflict detection, asyncio.run per event)
- Updated app/main.py (includes files_router and kb_router)
- Updated docker-compose.dev.yml (adds workspace-watcher service)
- Created tests/test_sandbox.py (path traversal, null byte, sibling prefix, dotdot inside allowed)
- Created tests/test_chunker.py (overlap continuity, code 500/100, default 1000/200, page numbers, sequential index)
- Created tests/test_kb.py (index txt, search, re-index replaces chunks, monkeypatched embeddings)
