from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards.reply.admin_menu import get_admin_menu
from bot.keyboards.reply.user_menu import get_user_main_menu


def _is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id if update.effective_user else 0
    return user_id in context.application.bot_data["settings"].admin_ids


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
    context.user_data["ui_mode"] = "admin"
    await update.message.reply_text(
        "🛠️ Режим администратора включён.",
        reply_markup=get_admin_menu(),
    )
