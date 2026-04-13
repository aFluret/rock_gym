from __future__ import annotations

from bot.utils.phone_formatter import normalize_phone


def validate_name(name: str) -> tuple[bool, str]:
    candidate = name.strip()
    if len(candidate) < 2:
        return False, "Имя слишком короткое. Напишите, пожалуйста, имя от 2 символов."
    if any(char.isdigit() for char in candidate):
        return False, "Имя не должно содержать цифры. Пример: Анна."
    return True, candidate


def validate_phone(raw_phone: str) -> tuple[bool, str]:
    normalized = normalize_phone(raw_phone)
    if not normalized:
        return False, "Не удалось распознать номер. Напишите в формате +375XXXXXXXXX."
    return True, normalized
