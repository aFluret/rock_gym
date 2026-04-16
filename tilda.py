from __future__ import annotations

import asyncio
import logging
import os

from flask import Blueprint, Flask, request
from telegram import Bot

from bot.integrations.tilda_service import handle_tilda_booking
from config import get_settings

LOGGER = logging.getLogger(__name__)
tilda_bp = Blueprint("tilda", __name__)


def _process_webhook() -> tuple[str, int]:
    try:
        settings = get_settings()
        if not settings.bot_token:
            return "BOT_TOKEN not set", 500
        if not settings.admin_ids:
            return "ADMIN_IDS not set", 500
        form_data = request.form.to_dict()
        bot = Bot(token=settings.bot_token)
        success, message = asyncio.run(
            handle_tilda_booking(
                bot=bot,
                settings=settings,
                form_data=form_data,
            )
        )
        if success:
            return message, 200
        # Для Tilda возвращаем 200 и для дублей, чтобы система не ретраила один и тот же лид.
        return message, 200
    except ValueError as exc:
        return str(exc), 400
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Webhook error: %s", exc)
        return "Internal server error", 500


@tilda_bp.post("/tilda")
def tilda_webhook() -> tuple[str, int]:
    return _process_webhook()


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(tilda_bp)
    return app


if __name__ == "__main__":
    host = os.getenv("TILDA_WEBHOOK_HOST", "0.0.0.0")
    port = int(os.getenv("TILDA_WEBHOOK_PORT", "8080"))
    app = create_app()
    app.run(host=host, port=port)
