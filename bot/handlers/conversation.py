from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.ai.category_detector import detect_category
from bot.ai.context_manager import get_optimized_context
from bot.notifications.admin_notifier import send_user_question_notification
from database.queries import (
    get_latest_user_booking,
    has_user_trial_history,
    save_message,
    upsert_user,
)

LOGGER = logging.getLogger(__name__)


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
    if _should_forward_to_admin(user_text, answer):
        await send_user_question_notification(
            application=context.application,
            admin_ids=settings.admin_ids,
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
