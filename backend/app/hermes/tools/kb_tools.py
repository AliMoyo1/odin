from __future__ import annotations

import json

from pydantic import BaseModel

from app.hermes.tools.registry import registry


class SearchKnowledgeInput(BaseModel):
    query: str
    project_id: str | None = None
    k: int = 5


async def _search_knowledge(
    inputs: SearchKnowledgeInput,
    session=None,
    user_id: str | None = None,
) -> str:
    if session is None or not user_id:
        return json.dumps({"ok": False, "error": "no database session"})

    try:
        from app.services.kb_search import search
        results = await search(
            session,
            user_id=user_id,
            query=inputs.query,
            project_id=inputs.project_id,
            k=inputs.k,
        )
        if not results:
            return json.dumps({"ok": True, "results": [], "message": "No relevant documents found."})

        formatted = [
            {
                "content": r.content,
                "citation": r.citation,
                "file_name": r.file_name,
                "page_number": r.page_number,
                "section_ref": r.section_ref,
            }
            for r in results
        ]
        return json.dumps({"ok": True, "results": formatted})
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


registry.register(
    "search_knowledge",
    "Search the personal knowledge base for documents and notes relevant to the query. Returns chunks with source citations.",
    SearchKnowledgeInput,
    _search_knowledge,
)
