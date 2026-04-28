from __future__ import annotations

from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot.handlers.admin.broadcast import build_broadcast_conversation
from bot.handlers.admin.admin_management import build_owner_admin_handlers
from bot.handlers.admin.dashboard import show_pending, show_stats
from bot.handlers.admin.notifications import handle_admin_action
from bot.handlers.booking.flow import build_booking_conversation
from bot.handlers.conversation import handle_ai_dialog
from bot.handlers.fallback import fallback_unknown
from bot.handlers.info.faq import handle_faq_callback, show_faq
from bot.handlers.info.locations import show_locations
from bot.handlers.info.prices import show_prices
from bot.handlers.start import start_command
from bot.middleware.anti_spam import check_text_spam
from bot.middleware.rate_limit import is_rate_limited


MENU_TEXTS = {
    "💬 Задать вопрос",
    "📅 Записаться",
    "💰 Цены и скидки",
    "📍 Адреса залов",
    "❓ FAQ: Часто задаваемые вопросы",
    "❓ Помощь",
    "🔔 Необработанные",
    "📊 Статистика",
    "📢 Рассылка",
    "📋 Все заявки",
    "🛡️ Управление администраторами",
    "⬅️ Назад",
}


async def _anti_spam_guard(update, context) -> None:  # type: ignore[no-untyped-def]
    if not update.effective_user or not update.message or not update.message.text:
        return
    user_text = update.message.text.strip()
    if user_text in MENU_TEXTS:
        return
    is_spam, message = check_text_spam(update.effective_user.id, user_text)
    if not is_spam:
        return
    await update.message.reply_text(message or "Слишком много повторяющихся сообщений.")
    raise ApplicationHandlerStop


async def _rate_limit_guard(update, context) -> None:  # type: ignore[no-untyped-def]
    if not update.effective_user or not update.message:
        return
    settings = context.application.bot_data["settings"]
    if is_rate_limited(update.effective_user.id, settings.rate_limit_per_minute):
        await update.message.reply_text("Слишком много сообщений. Подождите минуту, пожалуйста.")
        raise ApplicationHandlerStop


def build_handlers(application: Application) -> None:
    owner_message_handler, owner_callback_handler = build_owner_admin_handlers()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("prices", show_prices))
    application.add_handler(build_booking_conversation())

    application.add_handler(MessageHandler(filters.Regex("^💰 Цены и скидки$"), show_prices))
    application.add_handler(MessageHandler(filters.Regex("^📍 Адреса залов$"), show_locations))
    application.add_handler(MessageHandler(filters.Regex(r"^❓ (FAQ: Часто задаваемые вопросы|Помощь)$"), show_faq))

    application.add_handler(MessageHandler(filters.Regex("^🔔 Необработанные$"), show_pending))
    application.add_handler(MessageHandler(filters.Regex("^📊 Статистика$"), show_stats))
    application.add_handler(MessageHandler(filters.Regex("^📋 Все заявки$"), show_pending))
    application.add_handler(build_broadcast_conversation())
    application.add_handler(owner_message_handler)

    application.add_handler(CallbackQueryHandler(handle_admin_action, pattern=r"^adm:"))
    application.add_handler(owner_callback_handler)
    application.add_handler(CallbackQueryHandler(handle_faq_callback, pattern=r"^faq:"))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _anti_spam_guard), group=1)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _rate_limit_guard), group=2)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_dialog), group=3)
    application.add_handler(MessageHandler(filters.COMMAND, fallback_unknown), group=4)
