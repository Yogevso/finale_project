"""
Y15-023: Orphaned Job Cleanup

Cleanup background jobs for documents/attachments that no longer exist.
This handles cases where a document or attachment was deleted while
a conversion job was pending.

Usage:
    python -m scripts.orphan_job_cleanup --dry-run
    python -m scripts.orphan_job_cleanup --cleanup
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Attachment, AttachmentConversionJob, Document, DomainEventOutbox

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def find_orphaned_conversion_jobs(session) -> list[AttachmentConversionJob]:
    """Find conversion jobs whose attachments no longer exist."""
    # Get all pending/running jobs
    jobs = (
        session.query(AttachmentConversionJob)
        .filter(AttachmentConversionJob.status.in_(["pending", "running"]))
        .all()
    )
    
    orphaned = []
    for job in jobs:
        # Check if attachment still exists
        attachment = (
            session.query(Attachment)
            .filter(Attachment.id == job.attachment_id)
            .first()
        )
        if not attachment:
            orphaned.append(job)
            continue
        
        # Check if parent document still exists
        document = (
            session.query(Document)
            .filter(Document.id == attachment.document_id)
            .first()
        )
        if not document:
            orphaned.append(job)
    
    return orphaned


def find_orphaned_domain_events(session) -> list[DomainEventOutbox]:
    """Find domain events referencing deleted documents."""
    import json
    
    # Get pending events
    events = (
        session.query(DomainEventOutbox)
        .filter(DomainEventOutbox.status == "pending")
        .all()
    )
    
    orphaned = []
    for event in events:
        try:
            payload = json.loads(event.payload_json)
            document_id = payload.get("document_id")
            
            if document_id:
                document = (
                    session.query(Document)
                    .filter(Document.id == document_id)
                    .first()
                )
                if not document:
                    orphaned.append(event)
        except (json.JSONDecodeError, KeyError):
            # Can't parse payload, skip
            continue
    
    return orphaned


def cleanup_orphaned_jobs(session, jobs: list[AttachmentConversionJob]) -> tuple[int, int]:
    """Mark orphaned jobs as failed."""
    cleaned = 0
    failed = 0
    
    for job in jobs:
        try:
            job.status = "failed"
            job.finished_at = datetime.utcnow()
            job.last_error = "Attachment or document deleted while job was pending"
            cleaned += 1
            logger.info(f"Marked job {job.id} as failed (orphaned)")
        except Exception as e:
            failed += 1
            logger.error(f"Failed to mark job {job.id}: {e}")
    
    if cleaned > 0:
        session.commit()
    
    return cleaned, failed


def cleanup_orphaned_events(session, events: list[DomainEventOutbox]) -> tuple[int, int]:
    """Mark orphaned events as failed."""
    cleaned = 0
    failed = 0
    
    for event in events:
        try:
            event.status = "failed"
            event.processed_at = datetime.utcnow()
            event.last_error = "Referenced document no longer exists"
            cleaned += 1
            logger.info(f"Marked event {event.id} as failed (orphaned)")
        except Exception as e:
            failed += 1
            logger.error(f"Failed to mark event {event.id}: {e}")
    
    if cleaned > 0:
        session.commit()
    
    return cleaned, failed


def main():
    parser = argparse.ArgumentParser(
        description="Find and clean up orphaned background jobs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only list orphaned jobs, don't clean up",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Mark orphaned jobs as failed",
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
        # Find orphaned conversion jobs
        logger.info("Finding orphaned conversion jobs...")
        orphaned_jobs = find_orphaned_conversion_jobs(session)
        
        if orphaned_jobs:
            logger.info(f"Found {len(orphaned_jobs)} orphaned conversion jobs:")
            for job in orphaned_jobs:
                logger.info(f"  Job {job.id}: attachment_id={job.attachment_id}, type={job.job_type}")
        else:
            logger.info("No orphaned conversion jobs found")
        
        # Find orphaned domain events
        logger.info("Finding orphaned domain events...")
        orphaned_events = find_orphaned_domain_events(session)
        
        if orphaned_events:
            logger.info(f"Found {len(orphaned_events)} orphaned domain events:")
            for event in orphaned_events:
                logger.info(f"  Event {event.id}: type={event.event_type}")
        else:
            logger.info("No orphaned domain events found")
        
        if args.cleanup:
            if orphaned_jobs:
                cleaned, failed = cleanup_orphaned_jobs(session, orphaned_jobs)
                logger.info(f"Conversion jobs: {cleaned} cleaned, {failed} failed")
            
            if orphaned_events:
                cleaned, failed = cleanup_orphaned_events(session, orphaned_events)
                logger.info(f"Domain events: {cleaned} cleaned, {failed} failed")
    
    finally:
        session.close()


if __name__ == "__main__":
    main()
