from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from data.gym_info import DISCOUNTS, PRICES


async def show_prices(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    text = (
        "💰 Цены Rock Gym\n\n"
        f"• {PRICES['trial']}\n"
        f"• {PRICES['abonement_12']}\n"
        f"• {PRICES['unlimited']}\n"
        f"• {PRICES['personal']}\n\n"
        "🎁 Скидки на абонементы:\n"
        f"• {DISCOUNTS[0]}\n• {DISCOUNTS[1]}\n• {DISCOUNTS[2]}\n• {DISCOUNTS[3]}"
    )
    await update.message.reply_text(text)
