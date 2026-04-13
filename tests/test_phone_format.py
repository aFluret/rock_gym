from bot.utils.phone_formatter import normalize_phone


def test_normalize_phone_plus375() -> None:
    assert normalize_phone("+375 (29) 123-45-67") == "+375291234567"


def test_normalize_phone_local() -> None:
    assert normalize_phone("291234567") == "+375291234567"
