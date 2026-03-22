"""FIX-004d: Find and deactivate orphaned users (tenant_id=None, role != SYSTEM_ADMIN).

Usage:
    python scripts/fix_orphaned_users.py          # Dry-run (report only)
    python scripts/fix_orphaned_users.py --apply   # Deactivate orphaned users
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal
from app.models import User, UserRole


def find_orphaned_users(db):
    return (
        db.query(User)
        .filter(User.tenant_id.is_(None), User.role != UserRole.SYSTEM_ADMIN)
        .all()
    )


def main():
    parser = argparse.ArgumentParser(description="Find and deactivate orphaned users without tenant_id")
    parser.add_argument("--apply", action="store_true", help="Actually deactivate orphaned users")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        orphans = find_orphaned_users(db)
        if not orphans:
            print("No orphaned users found.")
            return

        print(f"Found {len(orphans)} orphaned user(s) (tenant_id=None, role != SYSTEM_ADMIN):")
        for u in orphans:
            print(f"  ID={u.id}  email={u.email}  role={u.role}  active={u.is_active}")

        if args.apply:
            for u in orphans:
                u.is_active = False
            db.commit()
            print(f"\nDeactivated {len(orphans)} orphaned user(s).")
        else:
            print("\nDry run — pass --apply to deactivate these users.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
