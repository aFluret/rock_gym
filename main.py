from __future__ import annotations

import asyncio

from telegram.ext import Application

from bot.ai.groq_service import GroqService
from bot.handlers import build_handlers
from bot.integrations import IntegrationService
from bot.middleware.logging import configure_logging
from bot.notifications.reminder_scheduler import start_reminder_scheduler
from config import get_settings
from database.db import init_database
from database.queries import bootstrap_admins


async def run() -> None:
    settings = get_settings()
    if not settings.bot_token:
        raise RuntimeError("Укажите BOT_TOKEN в .env")

    configure_logging(settings.log_level)
    init_database(settings.database_path)
    bootstrap_admins(settings.database_path, settings.owner_id, settings.admin_ids)

    application = Application.builder().token(settings.bot_token).build()
    application.bot_data["settings"] = settings
    application.bot_data["groq_service"] = GroqService(
        settings.groq_api_key,
        settings.groq_model,
        max_retries=settings.groq_max_retries,
        retry_backoff_seconds=settings.groq_retry_backoff_seconds,
    )
    application.bot_data["integration_service"] = IntegrationService(
        crm_webhook_url=settings.crm_webhook_url,
    )

    build_handlers(application)
    start_reminder_scheduler(application, settings.database_path, settings)

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    try:
        await asyncio.Event().wait()
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    asyncio.run(run())
