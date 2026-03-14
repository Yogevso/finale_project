"""
Y15-022: Orphaned File Cleanup Job

Scheduled task to find storage files without corresponding DB records.
Files are logged for manual review rather than automatically deleted.

Usage:
    python -m scripts.orphan_file_cleanup --dry-run
    python -m scripts.orphan_file_cleanup --cleanup
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Attachment
from app.services.attachment_service import get_storage_backend

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_db_storage_keys(session) -> set[str]:
    """Get all storage keys from the database."""
    attachments = session.query(Attachment.storage_key).all()
    return {att.storage_key for att in attachments if att.storage_key}


def list_storage_files(storage, prefix: str = "") -> list[str]:
    """List all files in storage with the given prefix."""
    try:
        if hasattr(storage, "list_files"):
            return storage.list_files(prefix)
        
        # Fallback for local storage
        upload_dir = Path(settings.UPLOAD_DIR)
        if not upload_dir.exists():
            return []
        
        files = []
        for root, _, filenames in os.walk(upload_dir):
            for filename in filenames:
                full_path = Path(root) / filename
                files.append(str(full_path))
        return files
    except Exception as e:
        logger.error(f"Failed to list storage files: {e}")
        return []


def find_orphaned_files(
    storage_files: list[str],
    db_storage_keys: set[str],
    min_age_hours: int = 24,
) -> list[str]:
    """Find storage files that don't have corresponding DB records.
    
    Only considers files older than min_age_hours to avoid flagging
    files that are currently being uploaded.
    """
    orphaned = []
    cutoff_time = datetime.utcnow() - timedelta(hours=min_age_hours)
    
    for file_path in storage_files:
        # Skip if file is in DB
        if file_path in db_storage_keys:
            continue
        
        # Check file age
        try:
            stat = os.stat(file_path) if os.path.exists(file_path) else None
            if stat:
                file_mtime = datetime.fromtimestamp(stat.st_mtime)
                if file_mtime > cutoff_time:
                    # File is too recent, might still be in flight
                    continue
        except OSError:
            pass
        
        orphaned.append(file_path)
    
    return orphaned


def main():
    parser = argparse.ArgumentParser(
        description="Find and optionally clean up orphaned storage files"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only list orphaned files, don't delete",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete orphaned files (requires confirmation)",
    )
    parser.add_argument(
        "--min-age-hours",
        type=int,
        default=24,
        help="Minimum age in hours for a file to be considered orphaned (default: 24)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Write orphaned file list to this file",
    )
    args = parser.parse_args()

    if args.cleanup and args.dry_run:
        logger.error("Cannot specify both --dry-run and --cleanup")
        sys.exit(1)

    if not args.cleanup and not args.dry_run:
        args.dry_run = True
        logger.info("No action specified, defaulting to --dry-run")

    # Connect to database
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Get storage backend
        storage = get_storage_backend()
        
        # Get DB storage keys
        logger.info("Fetching storage keys from database...")
        db_storage_keys = get_db_storage_keys(session)
        logger.info(f"Found {len(db_storage_keys)} attachments in database")
        
        # List storage files
        logger.info("Listing storage files...")
        storage_files = list_storage_files(storage)
        logger.info(f"Found {len(storage_files)} files in storage")
        
        # Find orphaned files
        logger.info(f"Checking for orphaned files (min age: {args.min_age_hours} hours)...")
        orphaned_files = find_orphaned_files(
            storage_files, db_storage_keys, args.min_age_hours
        )
        
        if not orphaned_files:
            logger.info("No orphaned files found")
            return
        
        logger.info(f"Found {len(orphaned_files)} orphaned files")
        
        # Output orphaned files
        if args.output:
            with open(args.output, "w") as f:
                for file_path in orphaned_files:
                    f.write(f"{file_path}\n")
            logger.info(f"Wrote orphaned file list to {args.output}")
        else:
            logger.info("Orphaned files:")
            for file_path in orphaned_files:
                logger.info(f"  {file_path}")
        
        if args.cleanup:
            logger.warning(f"About to delete {len(orphaned_files)} orphaned files")
            confirm = input("Type 'DELETE' to confirm: ")
            if confirm != "DELETE":
                logger.info("Cleanup cancelled")
                return
            
            deleted = 0
            failed = 0
            for file_path in orphaned_files:
                try:
                    storage.delete(file_path)
                    deleted += 1
                    logger.info(f"Deleted: {file_path}")
                except Exception as e:
                    failed += 1
                    logger.error(f"Failed to delete {file_path}: {e}")
            
            logger.info(f"Cleanup complete: {deleted} deleted, {failed} failed")
    
    finally:
        session.close()


if __name__ == "__main__":
    main()
