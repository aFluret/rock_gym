from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from telegram import Bot

from bot.notifications.admin_notifier import (
    send_admin_text_notification,
    send_booking_notification,
)
from bot.security import get_admin_recipient_ids
from bot.utils.phone_formatter import normalize_phone
from config import Settings
from database.queries import create_booking, track_event

_NAME_KEYS = ("Name", "name", "NAME", "Имя")
_PHONE_KEYS = ("Phone", "phone", "PHONE", "Телефон")
_GYM_KEYS = ("gym", "Gym", "GYM", "Зал")
_TRAINER_KEYS = ("trener", "Trener", "trainer", "Trainer", "Тренер", "ТРЕНЕР")
_SUBSCRIPTION_KEYS = ("tarif", "Tarif", "TARIF", "Тариф", "Абонемент", "subscription")
_QUESTION_KEYS = (
    "qest",
    "Qest",
    "question",
    "Question",
    "Комментарий",
    "comment",
    "message",
)
_CONTACT_FORM_TYPE_KEYS = ("formname", "form_name", "formtitle", "form_title")


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


def _pick_by_key_markers(form_data: Mapping[str, str], markers: tuple[str, ...]) -> str:
    lowered_markers = tuple(marker.lower() for marker in markers)
    for key, value in form_data.items():
        if not value:
            continue
        key_lower = key.lower()
        if any(marker in key_lower for marker in lowered_markers):
            return value.strip()
    return ""


def _has_key_marker(form_data: Mapping[str, str], markers: tuple[str, ...]) -> bool:
    lowered_markers = tuple(marker.lower() for marker in markers)
    return any(any(marker in key.lower() for marker in lowered_markers) for key in form_data)


def _has_value_marker(form_data: Mapping[str, str], markers: tuple[str, ...]) -> bool:
    lowered_markers = tuple(marker.lower() for marker in markers)
    for value in form_data.values():
        candidate = value.strip().lower()
        if candidate and any(marker in candidate for marker in lowered_markers):
            return True
    return False


def _detect_form_type(
    form_data: Mapping[str, str],
) -> Literal["trial", "personal_training", "subscription", "contact", "unknown"]:
    if _has_key_marker(form_data, _GYM_KEYS):
        return "trial"
    if _has_key_marker(form_data, _TRAINER_KEYS):
        return "personal_training"
    if _has_key_marker(form_data, _SUBSCRIPTION_KEYS) or _has_value_marker(
        form_data, ("абонем", "subscription", "tarif", "тариф")
    ):
        return "subscription"
    if _has_key_marker(form_data, _QUESTION_KEYS) or _has_key_marker(form_data, _CONTACT_FORM_TYPE_KEYS):
        return "contact"
    return "unknown"


def parse_tilda_booking(form_data: Mapping[str, str]) -> tuple[str, str, str]:
    name = _pick_first_filled(form_data, _NAME_KEYS) or "Клиент с сайта"
    normalized_phone = normalize_phone(_pick_first_filled(form_data, _PHONE_KEYS))
    if not normalized_phone:
        raise ValueError("Невалидный номер телефона в заявке Tilda.")
    gym_location = _resolve_gym_location(_pick_first_filled(form_data, _GYM_KEYS))
    return name, normalized_phone, gym_location


def _build_tilda_text_notification(form_data: Mapping[str, str]) -> str:
    form_type = _detect_form_type(form_data)
    name = _pick_first_filled(form_data, _NAME_KEYS) or "Не указано"
    phone_raw = _pick_first_filled(form_data, _PHONE_KEYS)
    phone = normalize_phone(phone_raw) or phone_raw or "Не указано"

    if form_type == "personal_training":
        trainer = _pick_first_filled(form_data, _TRAINER_KEYS) or _pick_by_key_markers(
            form_data, ("тренер", "trainer", "trener")
        )
        trainer_text = trainer or "Не указан"
        return (
            "🟣 Заявка с сайта: Персональная тренировка\n\n"
            f"👤 Имя: {name}\n"
            f"📞 Телефон: {phone}\n"
            f"🏋️ Тренер: {trainer_text}"
        )

    if form_type == "subscription":
        plan = _pick_first_filled(form_data, _SUBSCRIPTION_KEYS) or _pick_by_key_markers(
            form_data, ("абонем", "тариф", "subscription", "tarif")
        )
        plan_text = plan or "Не указан"
        return (
            "🟢 Заявка с сайта: Покупка абонемента\n\n"
            f"👤 Имя: {name}\n"
            f"📞 Телефон: {phone}\n"
            f"📋 Запрос: {plan_text}"
        )

    if form_type in {"contact", "unknown"}:
        question = _pick_first_filled(form_data, _QUESTION_KEYS) or _pick_by_key_markers(
            form_data, ("коммент", "вопрос", "message", "comment")
        )
        question_text = question or "Без комментария"
        return (
            "🟡 Заявка с сайта: Обратная связь\n\n"
            f"👤 Имя: {name}\n"
            f"📞 Телефон: {phone}\n"
            f"💬 Комментарий: {question_text}"
        )

    return (
        "🟡 Заявка с сайта\n\n"
        f"👤 Имя: {name}\n"
        f"📞 Телефон: {phone}"
    )


async def handle_tilda_booking(
    *,
    bot: Bot,
    settings: Settings,
    form_data: Mapping[str, str],
) -> tuple[bool, str]:
    form_type = _detect_form_type(form_data)
    if form_type != "trial":
        await send_admin_text_notification(
            bot=bot,
            admin_ids=get_admin_recipient_ids(settings),
            text=_build_tilda_text_notification(form_data),
        )
        track_event(
            settings.database_path,
            "tilda_form_received",
            payload={"source": "tilda", "form_type": form_type},
        )
        return True, f"Обработана форма {form_type}."

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
        admin_ids=get_admin_recipient_ids(settings),
        booking_id=booking_number,
        name=name,
        phone=phone,
        gym_location=gym_location,
        telegram_id=None,
    )
    return True, f"Создана заявка #{booking_number}."
