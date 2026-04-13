from __future__ import annotations

import re


def normalize_phone(raw_phone: str) -> str | None:
    digits = re.sub(r"\D", "", raw_phone)
    if digits.startswith("80") and len(digits) == 11:
        digits = f"375{digits[2:]}"
    if digits.startswith("375") and len(digits) == 12:
        return f"+{digits}"
    if len(digits) == 9:
        return f"+375{digits}"
    return None


def display_phone(phone: str) -> str:
    normalized = normalize_phone(phone) or phone
    if not normalized.startswith("+375") or len(normalized) != 13:
        return normalized
    return f"+375 ({normalized[4:6]}) {normalized[6:9]}-{normalized[9:11]}-{normalized[11:13]}"
