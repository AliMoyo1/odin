from __future__ import annotations

from datetime import datetime, timezone


def build_system_prompt(
    user_email: str,
    project_name: str | None = None,
    project_description: str | None = None,
    workspace_path: str | None = None,
    memories: list[str] | None = None,
    rag_chunks: list[str] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    parts = [
        "You are Hermes, the AI core of ODIN. Your purpose is to help the user accomplish tasks, manage their knowledge, and automate their workflows.",
        f"Current UTC date/time: {now.strftime('%Y-%m-%d %H:%M UTC')}",
        "You have access to tools. Use them when appropriate. Always prefer accuracy over speed.",
    ]

    if project_name:
        project_block = f"Active project: {project_name}"
        if project_description:
            project_block += f"\nDescription: {project_description}"
        if workspace_path:
            project_block += f"\nWorkspace path: {workspace_path}"
        parts.append(project_block)

    if memories:
        mem_block = "Relevant memories:\n" + "\n".join(f"- {m}" for m in memories)
        parts.append(mem_block)

    if rag_chunks:
        rag_block = "Reference knowledge:\n"
        for i, chunk in enumerate(rag_chunks, 1):
            rag_block += f"[Source {i}]: {chunk}\n"
        rag_block += "Cite sources using [Source: N] notation when using this information."
        parts.append(rag_block)

    parts.append(
        "Tool conduct rules:\n"
        "- For destructive or write operations, ask the user for confirmation if you are not certain they want to proceed.\n"
        "- Never fabricate file contents. Only report what you actually read.\n"
        "- If a tool returns an error, report it clearly to the user."
    )

    return "\n\n".join(parts)
