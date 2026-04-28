from __future__ import annotations

from telegram import KeyboardButton, ReplyKeyboardMarkup


def get_admin_menu(*, show_owner_tools: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("🔔 Необработанные"), KeyboardButton("📊 Статистика")],
        [KeyboardButton("📢 Рассылка"), KeyboardButton("📋 Все заявки")],
    ]
    if show_owner_tools:
        keyboard.append([KeyboardButton("🛡️ Управление администраторами")])
    keyboard.extend(
        [
        [KeyboardButton("👤 Переключиться на режим клиента")],
        ]
    )
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
