from __future__ import annotations


def detect_category(user_text: str) -> str | None:
    text = user_text.lower()
    if any(keyword in text for keyword in ("студент", "универ", "университет", "колледж")):
        return "student"
    if any(keyword in text for keyword in ("школьник", "школа", "9 класс", "10 класс", "11 класс")):
        return "schoolkid"
    if any(keyword in text for keyword in ("декрет", "мама", "после родов")):
        return "maternity"
    return None
