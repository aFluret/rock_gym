from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from data.gym_info import DISCOUNTS, PRICES


async def show_prices(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    text = (
        "💰 Цены Rock Gym\n\n"
        "🕒 Абонементы в любое время:\n"
        f"• {PRICES['anytime_4']}\n"
        f"• {PRICES['anytime_8']}\n"
        f"• {PRICES['anytime_12']}\n"
        f"• {PRICES['anytime_1_month']}\n"
        f"• {PRICES['anytime_3_months']}\n"
        f"• {PRICES['anytime_6_months']}\n"
        f"• {PRICES['anytime_12_months']}\n\n"
        "🌤 Абонементы до 17:00:\n"
        f"• {PRICES['before_17_4']}\n"
        f"• {PRICES['before_17_8']}\n"
        f"• {PRICES['before_17_12']}\n"
        f"• {PRICES['before_17_1_month']}\n"
        f"• {PRICES['before_17_3_months']}\n"
        f"• {PRICES['before_17_6_months']}\n"
        f"• {PRICES['before_17_12_months']}\n\n"
        "➕ Дополнительные услуги:\n"
        f"• {PRICES['personal']}\n\n"
        "Разовые посещения:\n"
        f"• {PRICES['trial_first']}\n"
        f"• {PRICES['single_before_17']}\n"
        f"• {PRICES['single_after_17']}\n\n"
        "🎯 Спецпредложение:\n"
        f"• {PRICES['light_month']}\n\n"
        "🎁 Скидки на абонементы:\n"
        f"• {DISCOUNTS[0]}\n• {DISCOUNTS[1]}\n• {DISCOUNTS[2]}\n• {DISCOUNTS[3]}"
    )
    await update.message.reply_text(text)
