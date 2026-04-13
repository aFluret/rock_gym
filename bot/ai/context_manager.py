from __future__ import annotations

from pathlib import Path

from bot.ai.system_prompt import build_system_prompt
from database.queries import fetch_conversation_messages


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def get_optimized_context(database_path: Path, conversation_id: int, max_tokens: int = 4000) -> list[dict[str, str]]:
    rows = fetch_conversation_messages(database_path, conversation_id)
    if not rows:
        return [{"role": "system", "content": build_system_prompt()}]

    context_messages: list[dict[str, str]] = [{"role": "system", "content": build_system_prompt()}]
    seen_contents: set[str] = set()

    important_rows = [row for row in rows if int(row["is_important"]) == 1]
    fresh_rows = rows[-30:]
    merged_rows = important_rows + fresh_rows

    for row in merged_rows:
        content = str(row["content"]).strip()
        if not content or content in seen_contents:
            continue
        seen_contents.add(content)
        context_messages.append({"role": str(row["role"]), "content": content})

    total_tokens = sum(_estimate_tokens(message["content"]) for message in context_messages)
    while total_tokens > max_tokens and len(context_messages) > 2:
        context_messages.pop(1)
        total_tokens = sum(_estimate_tokens(message["content"]) for message in context_messages)

    return context_messages
