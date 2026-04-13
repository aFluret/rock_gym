from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🏠 В главное меню", callback_data="back:main")]]
    )
