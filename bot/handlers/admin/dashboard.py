from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from data.gym_info import GYMS
from database.queries import get_funnel_stats, get_pending_bookings, get_stats_snapshot


def _is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id if update.effective_user else 0
    is_admin = user_id in context.application.bot_data["settings"].admin_ids
    is_admin_mode = context.user_data.get("ui_mode", "admin") == "admin"
    return is_admin and is_admin_mode


def _pending_actions_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Позвонили", callback_data=f"adm:ok:{booking_id}"),
            InlineKeyboardButton("🗓️ Напомнить", callback_data=f"adm:rm:{booking_id}"),
        ]]
    )


async def show_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not _is_admin(update, context):
        return
    rows = get_pending_bookings(context.application.bot_data["settings"].database_path)
    if not rows:
        await update.message.reply_text("✅ Необработанных заявок нет.")
        return
    await update.message.reply_text(f"🔔 Необработанные заявки: {len(rows)}")
    for row in rows:
        gym = GYMS[str(row["gym_location"])]["title"]
        await update.message.reply_text(
            f"🔴 #{row['id']} | {row['name']} | {row['phone']} | {gym}",
            reply_markup=_pending_actions_keyboard(int(row["id"])),
        )


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not _is_admin(update, context):
        return
    database_path = context.application.bot_data["settings"].database_path
    stats = get_stats_snapshot(database_path)
    funnel = get_funnel_stats(database_path, days=30)
    text = (
        "📊 Статистика заявок\n\n"
        f"Всего: {stats['total']}\n"
        f"В обработке: {stats['pending']}\n"
        f"Обработано: {stats['contacted']}\n"
        f"Конверсия обработки: {stats['conversion']}%\n\n"
        "🔎 Воронка за 30 дней\n"
        f"Стартов: {funnel['start']}\n"
        f"Начали запись: {funnel['booking_started']} ({funnel['start_to_booking_started']}%)\n"
        f"Подтвердили запись: {funnel['booking_confirmed']} ({funnel['booking_started_to_confirmed']}%)\n"
        f"Связались: {funnel['booking_contacted']} ({funnel['confirmed_to_contacted']}%)"
    )
    await update.message.reply_text(text)
