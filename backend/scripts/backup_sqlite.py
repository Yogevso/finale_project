"""SQLite backup automation script.

Creates a timestamped copy of the production database using the SQLite
online-backup API for a consistent snapshot.

Usage:
  python -m scripts.backup_sqlite                     # default: data/portal.db
  python -m scripts.backup_sqlite --db path/to/db     # custom path
  python -m scripts.backup_sqlite --dest /backups/    # custom destination dir

Restore:
  1. Stop the application
  2. cp data/portal.db.bak.<timestamp> data/portal.db
  3. Start the application
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def backup_database(db_path: Path, dest_dir: Path | None = None) -> Path:
    """Create a consistent backup of an SQLite database using the online-backup API.

    Returns the path to the backup file.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    if dest_dir is None:
        dest_dir = db_path.parent

    dest_dir.mkdir(parents=True, exist_ok=True)
    timestamp = int(time.time())
    backup_path = dest_dir / f"{db_path.stem}.db.bak.{timestamp}"

    src = sqlite3.connect(str(db_path))
    dst = sqlite3.connect(str(backup_path))
    try:
        src.backup(dst)
        logger.info("Backup created: %s (%.1f MB)", backup_path, backup_path.stat().st_size / 1024 / 1024)
    finally:
        dst.close()
        src.close()

    return backup_path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Back up SQLite database")
    parser.add_argument("--db", type=Path, default=Path("data/portal.db"), help="Database path")
    parser.add_argument("--dest", type=Path, default=None, help="Destination directory")
    args = parser.parse_args()

    path = backup_database(args.db, args.dest)
    print(f"Backup saved to: {path}")


if __name__ == "__main__":
    main()
