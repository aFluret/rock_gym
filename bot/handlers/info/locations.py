from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from data.gym_info import GYMS


async def show_locations(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    text = (
        "📍 Наши залы:\n\n"
        f"🏢 {GYMS['minsk']['title']}: {GYMS['minsk']['address']}\n"
        f"🕐 {GYMS['minsk']['hours']}\n"
        f"📞 {GYMS['minsk']['phone']}\n\n"
        f"🏢 {GYMS['lesnoy']['title']}: {GYMS['lesnoy']['address']}\n"
        f"🕐 {GYMS['lesnoy']['hours']}\n"
        f"📞 {GYMS['lesnoy']['phone']}"
    )
    await update.message.reply_text(text)
