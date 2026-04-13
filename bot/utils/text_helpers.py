from __future__ import annotations


def truncate_text(text: str, max_length: int = 900) -> str:
    if len(text) <= max_length:
        return text
    return f"{text[:max_length - 1]}…"
