from __future__ import annotations

from telegram import KeyboardButton, ReplyKeyboardMarkup


def get_user_main_menu(show_admin_return: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("💬 Задать вопрос"), KeyboardButton("📅 Записаться")],
        [KeyboardButton("💰 Цены и скидки"), KeyboardButton("📍 Адреса залов")],
        [KeyboardButton("❓ FAQ")],
    ]
    if show_admin_return:
        keyboard.append([KeyboardButton("🛠️ Вернуться в режим администратора")])
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выберите действие 👇",
    )
