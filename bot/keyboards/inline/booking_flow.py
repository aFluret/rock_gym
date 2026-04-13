from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def get_gym_selection_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🏢 Минск\n📍 Нёманская, 3", callback_data="gym:minsk")],
        [InlineKeyboardButton("🏢 Лесной\n📍 Мирная, 17в", callback_data="gym:lesnoy")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back:main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_phone_request_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("📱 Отправить номер", request_contact=True)],
        [KeyboardButton("✏️ Ввести вручную")],
        [KeyboardButton("⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Или напишите номер: +375...",
    )


def get_booking_confirmation_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data="book:confirm"),
            InlineKeyboardButton("✏️ Изменить", callback_data="book:edit"),
        ],
        [InlineKeyboardButton("❌ Отменить запись", callback_data="book:cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)
