from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.admin.admin_management import try_activate_admin_invite
from bot.keyboards.reply.admin_menu import get_admin_menu
from bot.keyboards.reply.user_menu import get_user_main_menu
from bot.security import is_admin, is_owner
from database.queries import track_event, upsert_user


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    settings = context.application.bot_data["settings"]
    start_payload = context.args[0].strip() if context.args else ""
    if start_payload and await try_activate_admin_invite(update, context, start_payload):
        return
    upsert_user(
        settings.database_path,
        update.effective_user.id,
        update.effective_user.username,
        update.effective_user.first_name,
    )
    track_event(settings.database_path, "start", telegram_id=update.effective_user.id)
    has_admin_access = is_admin(settings, update.effective_user.id)
    owner_access = is_owner(settings, update.effective_user.id)
    if has_admin_access and "ui_mode" not in context.user_data:
        context.user_data["ui_mode"] = "admin"

    is_client_mode = context.user_data.get("ui_mode", "client") == "client"
    if has_admin_access and not is_client_mode:
        reply_markup = get_admin_menu(show_owner_tools=owner_access)
    else:
        reply_markup = get_user_main_menu(show_admin_return=has_admin_access)
    if has_admin_access and not is_client_mode:
        welcome = (
            "Привет! Я AI-помощник Rock Gym 💪\n"
            "Буду рад помогать тебе с управлением Rock Gym"
        )
    else:
        welcome = (
            "Привет! Я AI-помощник Rock Gym 💪\n"
            "Помогу с вопросами, ценами и записью на бесплатную пробную тренировку."
        )
    await update.message.reply_text(welcome, reply_markup=reply_markup)
