from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.ai.category_detector import detect_category
from bot.ai.context_manager import get_optimized_context
from bot.notifications.admin_notifier import send_user_question_notification
from bot.security import get_admin_recipient_ids, is_admin
from database.queries import (
    get_latest_user_booking,
    has_user_trial_history,
    save_message,
    upsert_user,
)

LOGGER = logging.getLogger(__name__)


def _has_booking_success_claim(text: str) -> bool:
    lowered_text = text.lower()
    success_markers = (
        "успешно запис",
        "вы записаны",
        "вы записан",
        "готово! вы записаны",
        "запись подтверждена",
    )
    return any(marker in lowered_text for marker in success_markers)


def _is_booking_confirmation_message(user_text: str) -> bool:
    lowered_text = user_text.lower()
    confirmation_markers = (
        "подтвержда",
        "подтверждаю",
        "подтверждено",
        "подтвердил",
        "подтвердила",
    )
    return any(marker in lowered_text for marker in confirmation_markers)


def _normalize_ai_booking_answer(user_text: str, ai_answer: str, has_booking: bool) -> str:
    if has_booking:
        return ai_answer
    if not _is_booking_confirmation_message(user_text):
        return ai_answer
    if not _has_booking_success_claim(ai_answer):
        return ai_answer
    return (
        "Понял Вас. Пока не вижу оформленной записи в системе.\n"
        "Чтобы записаться, нажмите «📅 Записаться» и заполните короткую форму "
        "(зал, имя и телефон)."
    )


def _should_handle_ai_dialog(*, is_admin: bool, ui_mode: str) -> bool:
    if is_admin and ui_mode == "admin":
        return False
    return True


def _should_forward_to_admin(user_text: str, ai_answer: str) -> bool:
    lower_user_text = user_text.lower()
    lower_ai_answer = ai_answer.lower()
    direct_request_markers = (
        "администратор",
        "перезвон",
        "свяж",
        "контакт менеджера",
    )
    ai_escalation_markers = (
        "передать ваш запрос",
        "передам ваш запрос",
        "уточняет администратор",
        "передать администратору",
        "свяжется администратор",
    )
    if any(marker in lower_ai_answer for marker in ai_escalation_markers):
        return True
    if any(marker in lower_user_text for marker in direct_request_markers):
        return True
    return False


async def handle_ai_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user or not update.message.text:
        return
    if context.user_data.get("active_flow") in {"booking", "broadcast"}:
        return
    settings = context.application.bot_data["settings"]
    has_admin_access = is_admin(settings, update.effective_user.id)
    ui_mode = context.user_data.get("ui_mode", "admin" if has_admin_access else "client")
    if not _should_handle_ai_dialog(is_admin=has_admin_access, ui_mode=ui_mode):
        await update.message.reply_text(
            "Вы в режиме администратора. Используйте кнопки админ-меню "
            "или переключитесь в клиентский режим."
        )
        return
    groq_service = context.application.bot_data["groq_service"]
    user_text = update.message.text.strip()
    menu_buttons = {
        "💰 Цены и скидки",
        "📍 Адреса залов",
        "❓ FAQ: Часто задаваемые вопросы",
        "❓ Помощь",
        "📅 Записаться",
        "🔔 Необработанные",
        "📊 Статистика",
        "📢 Рассылка",
        "📋 Все заявки",
        "👤 Переключиться на режим клиента",
        "🛠️ Вернуться в режим администратора",
        "⬅️ Назад",
    }
    if user_text in menu_buttons:
        return
    if user_text == "💬 Задать вопрос":
        await update.message.reply_text("Напишите вопрос, и я отвечу коротко и по делу 🙂")
        return

    if any(phrase in user_text.lower() for phrase in ("я запис", "записан", "записалась", "записался")):
        latest_booking = get_latest_user_booking(settings.database_path, update.effective_user.id)
        if latest_booking:
            gym_title = "Минске" if latest_booking["gym_location"] == "minsk" else "Лесном"
            await update.message.reply_text(
                f"Да, Вы записаны. Последняя заявка #{latest_booking['id']} в зале в {gym_title}."
            )
            return

    upsert_user(
        settings.database_path,
        update.effective_user.id,
        update.effective_user.username,
        update.effective_user.first_name,
    )
    category = detect_category(user_text)
    if category:
        upsert_user(
            settings.database_path,
            update.effective_user.id,
            update.effective_user.username,
            update.effective_user.first_name,
            category=category,
        )

    save_message(settings.database_path, update.effective_user.id, "user", user_text, is_important=bool(category))
    messages = get_optimized_context(settings.database_path, update.effective_user.id)
    user_has_trial_history = has_user_trial_history(settings.database_path, update.effective_user.id)
    if user_has_trial_history:
        messages.append(
            {
                "role": "system",
                "content": (
                    "Пользователь уже записывался на пробную тренировку. "
                    "Не предлагай снова пробную, если пользователь сам не просит."
                ),
            }
        )
    try:
        answer = await groq_service.generate_reply(messages)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Groq request failed: %s", exc)
        answer = "Сейчас ответ AI временно недоступен. Могу помочь с записью на пробную тренировку 📅"

    if "запис" not in answer.lower() and len(messages) > 6 and not user_has_trial_history:
        answer = f"{answer}\n\nЕсли хотите, могу сразу записать Вас на бесплатную пробную 📅"
    latest_booking = get_latest_user_booking(settings.database_path, update.effective_user.id)
    answer = _normalize_ai_booking_answer(user_text, answer, has_booking=bool(latest_booking))
    if _should_forward_to_admin(user_text, answer):
        await send_user_question_notification(
            application=context.application,
            admin_ids=get_admin_recipient_ids(settings),
            telegram_id=update.effective_user.id,
            first_name=update.effective_user.first_name,
            username=update.effective_user.username,
            question_text=user_text,
        )
        answer = (
            "📝 Передал ваш вопрос администратору.\n"
            "Администратор свяжется с вами и ответит по вашему запросу."
        )
    save_message(settings.database_path, update.effective_user.id, "assistant", answer)
    await update.message.reply_text(answer)
