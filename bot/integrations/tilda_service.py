from __future__ import annotations

from collections.abc import Mapping

from telegram import Bot

from bot.notifications.admin_notifier import send_booking_notification
from bot.utils.phone_formatter import normalize_phone
from config import Settings
from database.queries import create_booking, track_event

_NAME_KEYS = ("Name", "name", "NAME", "Имя")
_PHONE_KEYS = ("Phone", "phone", "PHONE", "Телефон")
_GYM_KEYS = ("gym", "Gym", "GYM", "Зал")


def _pick_first_filled(form_data: Mapping[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = form_data.get(key, "").strip()
        if value:
            return value
    return ""


def _resolve_gym_location(raw_gym: str) -> str:
    normalized = raw_gym.lower()
    if any(marker in normalized for marker in ("лес", "les", "mirn", "мирн")):
        return "lesnoy"
    return "minsk"


def parse_tilda_booking(form_data: Mapping[str, str]) -> tuple[str, str, str]:
    name = _pick_first_filled(form_data, _NAME_KEYS) or "Клиент с сайта"
    normalized_phone = normalize_phone(_pick_first_filled(form_data, _PHONE_KEYS))
    if not normalized_phone:
        raise ValueError("Невалидный номер телефона в заявке Tilda.")
    gym_location = _resolve_gym_location(_pick_first_filled(form_data, _GYM_KEYS))
    return name, normalized_phone, gym_location


async def handle_tilda_booking(
    *,
    bot: Bot,
    settings: Settings,
    form_data: Mapping[str, str],
) -> tuple[bool, str]:
    name, phone, gym_location = parse_tilda_booking(form_data)
    success, booking_id = create_booking(
        settings.database_path,
        user_id=None,
        name=name,
        phone=phone,
        gym_location=gym_location,
    )
    if not success:
        return False, f"Дубликат заявки (#{booking_id})."
    booking_number = int(booking_id or 0)
    track_event(
        settings.database_path,
        "booking_created_from_tilda",
        booking_id=booking_number,
        payload={"source": "tilda"},
    )
    await send_booking_notification(
        bot=bot,
        admin_ids=settings.admin_ids,
        booking_id=booking_number,
        name=name,
        phone=phone,
        gym_location=gym_location,
        telegram_id=None,
    )
    return True, f"Создана заявка #{booking_number}."
