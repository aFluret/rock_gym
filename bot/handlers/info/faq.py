from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from data.faq_database import FAQ_ANSWERS


async def show_faq(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"❓ {key.capitalize()}", callback_data=f"faq:{key}")] for key in FAQ_ANSWERS]
    )
    await update.message.reply_text("Выберите вопрос:", reply_markup=keyboard)


async def handle_faq_callback(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.callback_query or not update.callback_query.data:
        return
    await update.callback_query.answer()
    key = update.callback_query.data.replace("faq:", "", 1)
    answer = FAQ_ANSWERS.get(key, "Уточните вопрос, и я помогу.")
    await update.callback_query.edit_message_text(f"❓ {key.capitalize()}\n\n{answer}")
