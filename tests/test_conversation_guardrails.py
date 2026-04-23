from bot.handlers.conversation import _normalize_ai_booking_answer, _should_handle_ai_dialog


def test_replaces_false_booking_confirmation_without_actual_booking() -> None:
    sanitized = _normalize_ai_booking_answer(
        user_text="подтверждаю",
        ai_answer="✅ Готово! Вы записаны на пробную тренировку.",
        has_booking=False,
    )
    assert "не вижу оформленной записи" in sanitized.lower()
    assert "записаны на пробную тренировку" not in sanitized.lower()


def test_keeps_booking_confirmation_when_booking_exists() -> None:
    original_answer = "✅ Готово! Вы записаны на пробную тренировку."
    sanitized = _normalize_ai_booking_answer(
        user_text="подтверждаю",
        ai_answer=original_answer,
        has_booking=True,
    )
    assert sanitized == original_answer


def test_keeps_regular_ai_answer_for_non_confirmation_message() -> None:
    original_answer = "Спасибо за вопрос! Вот цены на абонементы."
    sanitized = _normalize_ai_booking_answer(
        user_text="какие цены?",
        ai_answer=original_answer,
        has_booking=False,
    )
    assert sanitized == original_answer


def test_blocks_ai_dialog_for_admin_in_admin_mode() -> None:
    should_handle = _should_handle_ai_dialog(is_admin=True, ui_mode="admin")
    assert should_handle is False


def test_allows_ai_dialog_for_admin_in_client_mode() -> None:
    should_handle = _should_handle_ai_dialog(is_admin=True, ui_mode="client")
    assert should_handle is True
