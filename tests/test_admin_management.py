from pathlib import Path

from database.db import init_database
from database.queries import (
    add_admin,
    bootstrap_admins,
    consume_admin_invite,
    create_admin_invite,
    get_active_admin_ids,
    get_admin_invite,
    is_admin_user,
    mark_expired_admin_invites,
    remove_admin,
)


def test_bootstrap_adds_owner_and_admins(tmp_path: Path) -> None:
    database_path = tmp_path / "test.db"
    init_database(database_path)

    bootstrap_admins(database_path, owner_id=1001, admin_ids=(2001, 2002))

    assert set(get_active_admin_ids(database_path)) == {1001, 2001, 2002}


def test_invite_is_one_time_and_consumed(tmp_path: Path) -> None:
    database_path = tmp_path / "test.db"
    init_database(database_path)

    token, _ = create_admin_invite(database_path, owner_id=1001, ttl_minutes=5)
    assert consume_admin_invite(database_path, token, used_by=3001) is True
    assert consume_admin_invite(database_path, token, used_by=3002) is False


def test_expired_invite_marked_expired(tmp_path: Path) -> None:
    database_path = tmp_path / "test.db"
    init_database(database_path)

    token, _ = create_admin_invite(database_path, owner_id=1001, ttl_minutes=0)
    mark_expired_admin_invites(database_path)
    invite = get_admin_invite(database_path, token)

    assert invite is not None
    assert invite["status"] == "expired"


def test_add_and_remove_admin_updates_access(tmp_path: Path) -> None:
    database_path = tmp_path / "test.db"
    init_database(database_path)

    add_admin(database_path, telegram_id=7777, username="new_admin", owner_id=1001)
    assert is_admin_user(database_path, 7777) is True

    removed = remove_admin(database_path, 7777)
    assert removed is True
    assert is_admin_user(database_path, 7777) is False
