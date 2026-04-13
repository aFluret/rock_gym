from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_confirmation_keyboard(
    confirm_text: str = "✅ Да",
    cancel_text: str = "❌ Нет",
    confirm_data: str = "confirm:yes",
    cancel_data: str = "confirm:no",
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(confirm_text, callback_data=confirm_data),
            InlineKeyboardButton(cancel_text, callback_data=cancel_data),
        ]]
    )
