from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from database.queries import get_booking_by_id, mark_booking_contacted, save_reminder, track_event


async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.callback_query or not update.callback_query.data:
        return
    user_id = update.effective_user.id if update.effective_user else 0
    settings = context.application.bot_data["settings"]
    if user_id not in settings.admin_ids:
        await update.callback_query.answer("Недостаточно прав", show_alert=True)
        return
    await update.callback_query.answer()
    _, action, booking_id_raw = update.callback_query.data.split(":")
    booking_id = int(booking_id_raw)
    if action == "ok":
        changed = mark_booking_contacted(settings.database_path, booking_id)
        if changed:
            row = get_booking_by_id(settings.database_path, booking_id)
            track_event(
                settings.database_path,
                "booking_contacted",
                telegram_id=int(row["telegram_id"]) if row and row["telegram_id"] else None,
                booking_id=booking_id,
            )
            integration_service = context.application.bot_data.get("integration_service")
            if integration_service and row:
                await integration_service.on_booking_contacted(
                    {
                        "booking_id": booking_id,
                        "name": row["name"],
                        "phone": row["phone"],
                        "gym_location": row["gym_location"],
                    }
                )
        message = "✅ Статус обновлён: Позвонили." if changed else "Заявка уже обработана."
        await update.callback_query.edit_message_text(message)
        return
    if action == "rm":
        save_reminder(settings.database_path, booking_id, minutes=30)
        await update.callback_query.edit_message_text(
            f"⏰ Напоминание по заявке #{booking_id} поставлено на 30 минут."
        )
