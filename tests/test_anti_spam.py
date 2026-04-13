from bot.middleware.anti_spam import check_text_spam


def test_detect_duplicate_spam() -> None:
    user_id = 555
    assert check_text_spam(user_id, "Привет")[0] is False
    assert check_text_spam(user_id, "привет")[0] is False
    assert check_text_spam(user_id, "  Привет!!!")[0] is True
