from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes


async def fallback_unknown(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    if update.message.text and update.message.text.strip().split()[0].lower() in {"/cancel", "/start"}:
        return
    await update.message.reply_text(
        "Не понял запрос 🤔\n"
        "Выберите кнопку в меню или напишите вопрос в свободной форме."
    )
