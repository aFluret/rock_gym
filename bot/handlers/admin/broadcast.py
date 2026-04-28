from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.security import is_admin
from database.queries import get_all_user_telegram_ids

BROADCAST_TEXT = 0


def _is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id if update.effective_user else 0
    settings = context.application.bot_data["settings"]
    has_admin_access = is_admin(settings, user_id)
    is_admin_mode = context.user_data.get("ui_mode", "admin") == "admin"
    return has_admin_access and is_admin_mode


async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not _is_admin(update, context):
        return ConversationHandler.END
    context.user_data["active_flow"] = "broadcast"
    await update.message.reply_text(
        "📢 Введите текст рассылки.\n"
        "Отправьте /cancel для отмены."
    )
    return BROADCAST_TEXT


async def preview_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return BROADCAST_TEXT
    context.user_data["broadcast_text"] = update.message.text.strip()
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Отправить", callback_data="brd:send"),
        InlineKeyboardButton("❌ Отмена", callback_data="brd:cancel"),
    ]])
    await update.message.reply_text(
        f"Предпросмотр рассылки:\n\n{context.user_data['broadcast_text']}",
        reply_markup=keyboard,
    )
    return BROADCAST_TEXT


async def handle_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.callback_query or not update.callback_query.data or not _is_admin(update, context):
        return ConversationHandler.END
    await update.callback_query.answer()
    action = update.callback_query.data
    if action == "brd:cancel":
        await update.callback_query.edit_message_text("Рассылка отменена.")
        context.user_data.pop("active_flow", None)
        context.user_data.pop("broadcast_text", None)
        return ConversationHandler.END

    settings = context.application.bot_data["settings"]
    text = context.user_data.get("broadcast_text", "").strip()
    if not text:
        await update.callback_query.edit_message_text("Текст рассылки пуст. Начните заново.")
        return ConversationHandler.END

    recipients = get_all_user_telegram_ids(settings.database_path)
    success_count = 0
    for telegram_id in recipients:
        try:
            await context.application.bot.send_message(telegram_id, text)
            success_count += 1
        except Exception:  # noqa: BLE001
            continue
    await update.callback_query.edit_message_text(
        f"✅ Рассылка завершена. Доставлено: {success_count}/{len(recipients)}"
    )
    context.user_data.pop("active_flow", None)
    context.user_data.pop("broadcast_text", None)
    return ConversationHandler.END


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("active_flow", None)
    context.user_data.pop("broadcast_text", None)
    if update.message:
        await update.message.reply_text("Рассылка отменена.")
    return ConversationHandler.END


def build_broadcast_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📢 Рассылка$"), start_broadcast)],
        states={
            BROADCAST_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, preview_broadcast),
                CallbackQueryHandler(handle_broadcast_callback, pattern=r"^brd:"),
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_broadcast)],
        per_chat=True,
        per_user=True,
        per_message=False,
    )
