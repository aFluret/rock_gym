from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_pagination_keyboard(current_page: int, total_pages: int, callback_prefix: str) -> InlineKeyboardMarkup:
    row = []
    if current_page > 1:
        row.append(InlineKeyboardButton("⬅️", callback_data=f"{callback_prefix}:p:{current_page - 1}"))
    row.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        row.append(InlineKeyboardButton("➡️", callback_data=f"{callback_prefix}:p:{current_page + 1}"))
    keyboard = [row, [InlineKeyboardButton("🏠 В меню", callback_data="back:main")]]
    return InlineKeyboardMarkup(keyboard)
