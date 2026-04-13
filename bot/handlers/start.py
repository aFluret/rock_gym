from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards.reply.admin_menu import get_admin_menu
from bot.keyboards.reply.user_menu import get_user_main_menu
from database.queries import track_event, upsert_user


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    settings = context.application.bot_data["settings"]
    upsert_user(
        settings.database_path,
        update.effective_user.id,
        update.effective_user.username,
        update.effective_user.first_name,
    )
    track_event(settings.database_path, "start", telegram_id=update.effective_user.id)
    is_admin = update.effective_user.id in settings.admin_ids
    if is_admin and "ui_mode" not in context.user_data:
        context.user_data["ui_mode"] = "admin"

    is_client_mode = context.user_data.get("ui_mode", "client") == "client"
    if is_admin and not is_client_mode:
        reply_markup = get_admin_menu()
    else:
        reply_markup = get_user_main_menu(show_admin_return=is_admin)
    welcome = (
        "Привет! Я AI-помощник Rock Gym 💪\n"
        "Помогу с вопросами, ценами и записью на бесплатную пробную тренировку."
    )
    await update.message.reply_text(welcome, reply_markup=reply_markup)
