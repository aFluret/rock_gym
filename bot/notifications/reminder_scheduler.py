from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from database.queries import bump_reminder, ensure_pending_reminders, get_due_reminders


def start_reminder_scheduler(
    application: Application,
    database_path,
    admin_ids: tuple[int, ...],
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")

    async def _send_due_reminders() -> None:
        if not admin_ids:
            return
        ensure_pending_reminders(database_path, minutes=10)
        reminders = get_due_reminders(database_path)
        for reminder in reminders:
            text = (
                f"⏰ Напоминание по заявке #{reminder['booking_id']}\n"
                f"👤 {reminder['name']} | 📞 {reminder['phone']}"
            )
            for admin_id in admin_ids:
                await application.bot.send_message(admin_id, text)
            bump_reminder(database_path, int(reminder["id"]))

    scheduler.add_job(_send_due_reminders, "interval", minutes=2, max_instances=1)
    scheduler.start()
    return scheduler
