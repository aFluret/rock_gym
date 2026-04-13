from __future__ import annotations

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.handlers.booking.keyboards import (
    get_booking_confirmation_keyboard,
    get_gym_selection_keyboard,
    get_phone_request_keyboard,
)
from bot.handlers.booking.validators import validate_name, validate_phone
from bot.keyboards.reply.user_menu import get_user_main_menu
from bot.notifications.admin_notifier import send_booking_notification
from data.gym_info import GYMS, PRICES
from database.queries import (
    clear_booking_session,
    create_booking,
    get_latest_user_booking,
    get_booking_session,
    track_event,
    upsert_booking_session,
    upsert_user,
)

BOOK_GYM, BOOK_NAME, BOOK_PHONE, BOOK_CONFIRM = range(4)
STATE_TO_FSM = {
    "book_gym": BOOK_GYM,
    "book_name": BOOK_NAME,
    "book_phone": BOOK_PHONE,
    "book_confirm": BOOK_CONFIRM,
}


def _progress(step: int, total: int = 4) -> str:
    return f"[{'🟩' * step}{'⬜' * (total - step)}] Шаг {step}/{total}\n"


def _persist_booking_session(update: Update, context: ContextTypes.DEFAULT_TYPE, state: str) -> None:
    if not update.effective_user:
        return
    settings = context.application.bot_data["settings"]
    payload = {
        "booking_gym": context.user_data.get("booking_gym"),
        "booking_name": context.user_data.get("booking_name"),
        "booking_phone": context.user_data.get("booking_phone"),
    }
    upsert_booking_session(settings.database_path, update.effective_user.id, state, payload)


def _load_session_to_context(session: dict, context: ContextTypes.DEFAULT_TYPE) -> None:
    payload = session.get("payload", {})
    if not isinstance(payload, dict):
        return
    for key in ("booking_gym", "booking_name", "booking_phone"):
        if payload.get(key):
            context.user_data[key] = payload[key]


async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.effective_user:
        return ConversationHandler.END
    context.user_data["active_flow"] = "booking"
    settings = context.application.bot_data["settings"]
    latest_booking = get_latest_user_booking(settings.database_path, update.effective_user.id)
    if latest_booking and latest_booking["status"] == "contacted":
        await update.message.reply_text(
            "Вы уже были записаны на пробную тренировку ✅\n\n"
            "Повторно записываться на пробную не нужно. "
            "Можно прийти в любой зал в часы работы и оформить разовое посещение на месте,\n"
            f"или купить абонемент:\n• {PRICES['abonement_12']}\n• {PRICES['unlimited']}\n\n"
            f"🏢 {GYMS['minsk']['title']}: {GYMS['minsk']['hours']}\n"
            f"🏢 {GYMS['lesnoy']['title']}: {GYMS['lesnoy']['hours']}"
        )
        return await cancel_booking(update, context)
    session = get_booking_session(settings.database_path, update.effective_user.id)
    if session:
        _load_session_to_context(session, context)
        resumed_state = STATE_TO_FSM.get(session["state"])
        if resumed_state == BOOK_NAME:
            await update.message.reply_text(f"{_progress(2)}Продолжим запись. Напишите имя.")
            return BOOK_NAME
        if resumed_state == BOOK_PHONE:
            await update.message.reply_text(
                f"{_progress(3)}Продолжим запись. Отправьте номер телефона:",
                reply_markup=get_phone_request_keyboard(),
            )
            return BOOK_PHONE
        if resumed_state == BOOK_CONFIRM:
            gym_location = context.user_data.get("booking_gym", "minsk")
            gym_title = "Минск" if gym_location == "minsk" else "Лесной"
            await update.message.reply_text(
                (
                    f"{_progress(4)}Продолжим запись. Проверьте данные:\n\n"
                    f"👤 Имя: {context.user_data.get('booking_name', '-')}\n"
                    f"📞 Телефон: {context.user_data.get('booking_phone', '-')}\n"
                    f"🏢 Зал: {gym_title}"
                ),
                reply_markup=get_booking_confirmation_keyboard(),
            )
            return BOOK_CONFIRM

    track_event(settings.database_path, "booking_started", telegram_id=update.effective_user.id)
    await update.message.reply_text(
        f"{_progress(1)}Выберите зал для пробной тренировки:",
        reply_markup=get_gym_selection_keyboard(),
    )
    _persist_booking_session(update, context, "book_gym")
    return BOOK_GYM


async def select_gym(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.callback_query or not update.callback_query.data:
        return BOOK_GYM
    await update.callback_query.answer()
    data = update.callback_query.data
    if data == "back:main":
        await update.callback_query.edit_message_text("Возвращаю в меню.")
        return await cancel_booking(update, context)
    gym_location = data.replace("gym:", "", 1)
    context.user_data["booking_gym"] = gym_location
    _persist_booking_session(update, context, "book_name")
    await update.callback_query.edit_message_text(
        f"{_progress(2)}Как к Вам обращаться? Напишите имя."
    )
    return BOOK_NAME


async def collect_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return BOOK_NAME
    if update.message.text == "⬅️ Назад":
        return await start_booking(update, context)
    is_valid, result = validate_name(update.message.text)
    if not is_valid:
        await update.message.reply_text(result)
        return BOOK_NAME
    context.user_data["booking_name"] = result
    _persist_booking_session(update, context, "book_phone")
    await update.message.reply_text(
        f"{_progress(3)}Отправьте номер телефона:",
        reply_markup=get_phone_request_keyboard(),
    )
    return BOOK_PHONE


async def collect_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return BOOK_PHONE
    if update.message.text == "⬅️ Назад":
        await update.message.reply_text("Вернулись к вводу имени. Напишите имя:")
        return BOOK_NAME

    phone_candidate = update.message.text or ""
    if update.message.contact:
        phone_candidate = update.message.contact.phone_number

    is_valid, result = validate_phone(phone_candidate)
    if not is_valid:
        await update.message.reply_text(result)
        return BOOK_PHONE

    context.user_data["booking_phone"] = result
    _persist_booking_session(update, context, "book_confirm")
    gym_location = context.user_data.get("booking_gym", "minsk")
    gym_title = "Минск" if gym_location == "minsk" else "Лесной"
    await update.message.reply_text(
        (
            f"{_progress(4)}Проверьте данные:\n\n"
            f"👤 Имя: {context.user_data['booking_name']}\n"
            f"📞 Телефон: {result}\n"
            f"🏢 Зал: {gym_title}"
        ),
        reply_markup=get_booking_confirmation_keyboard(),
    )
    return BOOK_CONFIRM


async def booking_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.callback_query or not update.callback_query.data or not update.effective_user:
        return BOOK_CONFIRM
    await update.callback_query.answer()
    action = update.callback_query.data
    if action == "book:cancel":
        await update.callback_query.edit_message_text("Запись отменена.")
        return await cancel_booking(update, context)
    if action == "book:edit":
        await update.callback_query.edit_message_text("Хорошо, начнём заново.")
        await update.callback_query.message.reply_text(
            "Выберите зал:",
            reply_markup=get_gym_selection_keyboard(),
        )
        _persist_booking_session(update, context, "book_gym")
        return BOOK_GYM

    settings = context.application.bot_data["settings"]
    user_id = upsert_user(
        settings.database_path,
        update.effective_user.id,
        update.effective_user.username,
        update.effective_user.first_name,
        phone=context.user_data.get("booking_phone"),
    )
    success, booking_id = create_booking(
        settings.database_path,
        user_id,
        context.user_data.get("booking_name", ""),
        context.user_data.get("booking_phone", ""),
        context.user_data.get("booking_gym", "minsk"),
    )
    if not success:
        await update.callback_query.edit_message_text(
            f"⚠️ Такая заявка уже есть (#{booking_id}). Админ уже обработает её."
        )
        return await cancel_booking(update, context)
    track_event(
        settings.database_path,
        "booking_confirmed",
        telegram_id=update.effective_user.id,
        booking_id=int(booking_id or 0),
        payload={"gym_location": context.user_data.get("booking_gym", "minsk")},
    )

    await update.callback_query.edit_message_text(
        "✅ Готово! Вы записаны на пробную тренировку.\n"
        "Возьмите форму, чистую обувь, воду и приходите за 10 минут до начала."
    )
    await send_booking_notification(
        application=context.application,
        admin_ids=settings.admin_ids,
        booking_id=int(booking_id or 0),
        name=context.user_data.get("booking_name", ""),
        phone=context.user_data.get("booking_phone", ""),
        gym_location=context.user_data.get("booking_gym", "minsk"),
        telegram_id=update.effective_user.id,
    )
    integration_service = context.application.bot_data.get("integration_service")
    if integration_service:
        await integration_service.on_booking_created(
            {
                "booking_id": int(booking_id or 0),
                "telegram_id": update.effective_user.id,
                "name": context.user_data.get("booking_name", ""),
                "phone": context.user_data.get("booking_phone", ""),
                "gym_location": context.user_data.get("booking_gym", "minsk"),
            }
        )
    return await cancel_booking(update, context)


async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("active_flow", None)
    if update.effective_user:
        settings = context.application.bot_data["settings"]
        clear_booking_session(settings.database_path, update.effective_user.id)
    for key in ("booking_gym", "booking_name", "booking_phone"):
        context.user_data.pop(key, None)
    if update.effective_chat:
        await update.effective_chat.send_message(
            "🏠 Вы в главном меню.",
            reply_markup=get_user_main_menu(),
        )
    return ConversationHandler.END


def build_booking_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📅 Записаться$"), start_booking),
            MessageHandler(
                filters.Regex(r"(?i)\b(записат|запиши|хочу на пробн|пробн.*тренировк)\b"),
                start_booking,
            ),
        ],
        states={
            BOOK_GYM: [
                CallbackQueryHandler(select_gym, pattern=r"^(gym:|back:main)")
            ],
            BOOK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_name)],
            BOOK_PHONE: [
                MessageHandler(
                    (filters.CONTACT | filters.TEXT) & ~filters.COMMAND,
                    collect_phone,
                )
            ],
            BOOK_CONFIRM: [CallbackQueryHandler(booking_confirm_callback, pattern=r"^book:")],
        },
        fallbacks=[CommandHandler("cancel", cancel_booking)],
        per_chat=True,
        per_user=True,
        per_message=False,
    )
