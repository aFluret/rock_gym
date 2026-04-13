from __future__ import annotations

from telegram import KeyboardButton, ReplyKeyboardMarkup


def get_admin_menu() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("🔔 Необработанные"), KeyboardButton("📊 Статистика")],
        [KeyboardButton("📢 Рассылка"), KeyboardButton("📋 Все заявки")],
        [KeyboardButton("👤 Переключиться на режим клиента")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
