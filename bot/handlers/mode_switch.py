from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards.reply.admin_menu import get_admin_menu
from bot.keyboards.reply.user_menu import get_user_main_menu
from bot.security import is_admin, is_owner


def _is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id if update.effective_user else 0
    settings = context.application.bot_data["settings"]
    return is_admin(settings, user_id)


async def switch_to_client_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not _is_admin(update, context):
        return
    context.user_data["ui_mode"] = "client"
    await update.message.reply_text(
        "👤 Режим клиента включён. Теперь вы видите клиентское меню.",
        reply_markup=get_user_main_menu(show_admin_return=True),
    )


async def switch_to_admin_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not _is_admin(update, context):
        return
    settings = context.application.bot_data["settings"]
    user_id = update.effective_user.id if update.effective_user else 0
    context.user_data["ui_mode"] = "admin"
    await update.message.reply_text(
        "🛠️ Режим администратора включён.",
        reply_markup=get_admin_menu(show_owner_tools=is_owner(settings, user_id)),
    )
