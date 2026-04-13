from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

from config import get_settings


def run_backup() -> Path:
    settings = get_settings()
    database_path = settings.database_path
    backup_dir = Path("backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"rock_gym_{timestamp}.db"
    shutil.copy2(database_path, backup_path)
    return backup_path


if __name__ == "__main__":
    target = run_backup()
    print(f"Backup created: {target}")
