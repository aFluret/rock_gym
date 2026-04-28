from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes, MessageHandler, filters

from bot.keyboards.reply.admin_menu import get_admin_menu
from bot.security import is_owner
from database.queries import (
    add_admin,
    consume_admin_invite,
    create_admin_invite,
    get_active_admins,
    get_admin_invite,
    remove_admin,
    track_event,
    upsert_user,
)

OWNER_MENU_TEXT = "🛡️ Управление администраторами"


def _owner_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📋 Список администраторов", callback_data="ownadm:list"),
                InlineKeyboardButton("➕ Создать ссылку", callback_data="ownadm:new"),
            ],
            [InlineKeyboardButton("➖ Удалить администратора", callback_data="ownadm:remove_menu")],
        ]
    )


def _build_admin_rows_text(rows: list) -> str:
    if not rows:
        return "Список администраторов пуст."
    lines = ["👥 Администраторы:\n"]
    for row in rows:
        username = f"@{row['username']}" if row["username"] else "без username"
        lines.append(
            f"• ID: {row['telegram_id']} | {username} | добавлен: {row['created_at']}"
        )
    return "\n".join(lines)


def _remove_admin_keyboard(rows: list, owner_id: int) -> InlineKeyboardMarkup:
    keyboard: list[list[InlineKeyboardButton]] = []
    for row in rows:
        telegram_id = int(row["telegram_id"])
        if telegram_id == owner_id:
            continue
        username = f"@{row['username']}" if row["username"] else str(telegram_id)
        keyboard.append(
            [InlineKeyboardButton(f"Удалить {username}", callback_data=f"ownadm:rm:{telegram_id}")]
        )
    keyboard.append([InlineKeyboardButton("🔄 Обновить список", callback_data="ownadm:list")])
    return InlineKeyboardMarkup(keyboard)


async def _notify_removed_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    removed_telegram_id: int,
) -> bool:
    try:
        await context.application.bot.send_message(
            removed_telegram_id,
            "🚫 Ваш доступ администратора в Rock Gym Bot был отозван владельцем.\n"
            "Админ-функции больше недоступны.",
        )
        return True
    except Exception:  # noqa: BLE001
        if update.callback_query and update.callback_query.message:
            await update.callback_query.message.reply_text(
                f"⚠️ Администратор удалён, но уведомление пользователю {removed_telegram_id} не доставлено."
            )
        return False


async def show_owner_admin_management(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    settings = context.application.bot_data["settings"]
    if not is_owner(settings, update.effective_user.id):
        await update.message.reply_text("Недостаточно прав для управления администраторами.")
        return
    await update.message.reply_text(
        "🛡️ Панель владельца: управление администраторами.",
        reply_markup=_owner_actions_keyboard(),
    )


async def handle_owner_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.callback_query or not update.callback_query.data or not update.effective_user:
        return
    settings = context.application.bot_data["settings"]
    if not is_owner(settings, update.effective_user.id):
        await update.callback_query.answer("Недостаточно прав", show_alert=True)
        return
    await update.callback_query.answer()
    data = update.callback_query.data
    if data == "ownadm:list":
        rows = get_active_admins(settings.database_path)
        await update.callback_query.edit_message_text(
            _build_admin_rows_text(rows),
            reply_markup=_owner_actions_keyboard(),
        )
        return
    if data == "ownadm:new":
        token, invite_row = create_admin_invite(settings.database_path, settings.owner_id, ttl_minutes=5)
        bot_username = context.application.bot.username
        if not bot_username:
            bot_username = (await context.application.bot.get_me()).username or ""
        deep_link = f"https://t.me/{bot_username}?start=adm_{token}"
        track_event(
            settings.database_path,
            "owner_admin_invite_created",
            telegram_id=update.effective_user.id,
            payload={"expires_at": invite_row["expires_at"]},
        )
        await update.callback_query.edit_message_text(
            "🔗 Одноразовая ссылка создана.\n"
            f"Срок действия до: {invite_row['expires_at']} UTC\n\n"
            f"{deep_link}",
            reply_markup=_owner_actions_keyboard(),
        )
        return
    if data == "ownadm:remove_menu":
        rows = get_active_admins(settings.database_path)
        await update.callback_query.edit_message_text(
            "Выберите администратора для удаления:",
            reply_markup=_remove_admin_keyboard(rows, settings.owner_id),
        )
        return
    if data.startswith("ownadm:rm:"):
        telegram_id = int(data.split(":")[-1])
        if telegram_id == settings.owner_id:
            await update.callback_query.edit_message_text(
                "Владельца удалить нельзя.",
                reply_markup=_owner_actions_keyboard(),
            )
            return
        removed = remove_admin(settings.database_path, telegram_id)
        track_event(
            settings.database_path,
            "owner_admin_removed",
            telegram_id=update.effective_user.id,
            payload={"removed_telegram_id": telegram_id, "removed": removed},
        )
        if removed:
            await _notify_removed_admin(update, context, telegram_id)
        rows = get_active_admins(settings.database_path)
        await update.callback_query.edit_message_text(
            "✅ Администратор удалён." if removed else "Администратор уже был удалён.",
            reply_markup=_remove_admin_keyboard(rows, settings.owner_id),
        )


async def try_activate_admin_invite(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    start_payload: str,
) -> bool:
    if not update.message or not update.effective_user:
        return False
    if not start_payload.startswith("adm_"):
        return False
    settings = context.application.bot_data["settings"]
    token = start_payload.replace("adm_", "", 1).strip()
    if not token:
        await update.message.reply_text("Некорректная ссылка приглашения.")
        return True
    invite = get_admin_invite(settings.database_path, token)
    if not invite:
        await update.message.reply_text("Ссылка приглашения не найдена.")
        return True
    if invite["status"] != "active":
        await update.message.reply_text("Ссылка уже использована или истекла.")
        return True
    consumed = consume_admin_invite(settings.database_path, token, update.effective_user.id)
    if not consumed:
        await update.message.reply_text("Ссылка уже использована или истекла.")
        return True

    upsert_user(
        settings.database_path,
        update.effective_user.id,
        update.effective_user.username,
        update.effective_user.first_name,
    )
    add_admin(
        settings.database_path,
        update.effective_user.id,
        update.effective_user.username,
        settings.owner_id,
    )
    track_event(
        settings.database_path,
        "admin_invite_accepted",
        telegram_id=update.effective_user.id,
        payload={"created_by": invite["created_by"]},
    )
    await update.message.reply_text(
        "✅ Доступ администратора активирован.\n\n"
        "Что можно делать:\n"
        "• Просматривать необработанные заявки\n"
        "• Отмечать, что с клиентом связались\n"
        "• Смотреть статистику и запускать рассылки\n\n"
        "Используйте кнопки админ-меню ниже.",
        reply_markup=get_admin_menu(),
    )
    if settings.owner_id:
        try:
            username = f"@{update.effective_user.username}" if update.effective_user.username else "без username"
            await context.application.bot.send_message(
                settings.owner_id,
                f"🟢 Новый администратор подключён: {update.effective_user.id} ({username})",
            )
        except Exception:  # noqa: BLE001
            pass
    return True


def build_owner_admin_handlers() -> tuple[MessageHandler, CallbackQueryHandler]:
    return (
        MessageHandler(filters.Regex(f"^{OWNER_MENU_TEXT}$"), show_owner_admin_management),
        CallbackQueryHandler(handle_owner_admin_callback, pattern=r"^ownadm:"),
    )
