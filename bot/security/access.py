from __future__ import annotations

from config import Settings
from database.queries import get_active_admin_ids, is_admin_user


def is_owner(settings: Settings, user_id: int) -> bool:
    return bool(settings.owner_id) and user_id == settings.owner_id


def is_admin(settings: Settings, user_id: int) -> bool:
    if is_owner(settings, user_id):
        return True
    if user_id in settings.admin_ids:
        return True
    return is_admin_user(settings.database_path, user_id)


def get_admin_recipient_ids(settings: Settings) -> tuple[int, ...]:
    admin_ids = set(settings.admin_ids)
    if settings.owner_id:
        admin_ids.add(settings.owner_id)
    admin_ids.update(get_active_admin_ids(settings.database_path))
    return tuple(sorted(admin_ids))
