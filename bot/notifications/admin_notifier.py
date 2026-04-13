from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application

from bot.utils.phone_formatter import display_phone
from data.gym_info import GYMS


async def send_booking_notification(
    application: Application,
    admin_ids: tuple[int, ...],
    booking_id: int,
    name: str,
    phone: str,
    gym_location: str,
    telegram_id: int | None,
) -> None:
    if not admin_ids:
        return
    gym = GYMS[gym_location]
    text = (
        f"🔴 Новая заявка #{booking_id}\n\n"
        f"👤 {name}\n"
        f"📞 {display_phone(phone)}\n"
        f"🏢 {gym['title']} ({gym['address']})"
    )
    keyboard = [[
        InlineKeyboardButton("✅ Позвонили", callback_data=f"adm:ok:{booking_id}"),
        InlineKeyboardButton("🗓️ Напомнить", callback_data=f"adm:rm:{booking_id}"),
    ]]
    if telegram_id:
        keyboard[0].append(InlineKeyboardButton("💬 Написать", url=f"tg://user?id={telegram_id}"))
    for admin_id in admin_ids:
        await application.bot.send_message(
            chat_id=admin_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def send_user_question_notification(
    application: Application,
    admin_ids: tuple[int, ...],
    telegram_id: int,
    first_name: str | None,
    username: str | None,
    question_text: str,
) -> None:
    if not admin_ids:
        return
    display_name = first_name or "Пользователь"
    username_text = f"@{username}" if username else "без username"
    text = (
        "🟡 Вопрос от клиента\n\n"
        f"👤 {display_name} ({username_text})\n"
        f"🆔 {telegram_id}\n"
        f"❓ {question_text}"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("💬 Написать клиенту", url=f"tg://user?id={telegram_id}")]]
    )
    for admin_id in admin_ids:
        await application.bot.send_message(
            chat_id=admin_id,
            text=text,
            reply_markup=keyboard,
        )
