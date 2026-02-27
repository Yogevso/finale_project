"""Operator tooling for async job DLQ visibility and recovery.

Run examples:
  python -m app.workers.async_jobs_admin list --queue outbox --limit 20
  python -m app.workers.async_jobs_admin requeue --queue conversion --id 12 --reset-attempts
"""

from __future__ import annotations

import argparse

from app.db import init_db
from app.services.conversion_jobs import (
    list_dead_letter_conversion_jobs,
    requeue_dead_letter_conversion_job,
)
from app.services.outbox import (
    list_dead_letter_outbox_entries,
    requeue_dead_letter_outbox_entry,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Async job DLQ tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List failed (DLQ) jobs")
    list_parser.add_argument("--queue", choices=["outbox", "conversion"], required=True)
    list_parser.add_argument("--limit", type=int, default=20)

    requeue_parser = subparsers.add_parser("requeue", help="Requeue one failed job")
    requeue_parser.add_argument("--queue", choices=["outbox", "conversion"], required=True)
    requeue_parser.add_argument("--id", type=int, required=True)
    requeue_parser.add_argument("--reset-attempts", action="store_true")
    requeue_parser.add_argument(
        "--force",
        action="store_true",
        help="Conversion only: force regeneration on retry",
    )
    return parser.parse_args()


def _run_list(args: argparse.Namespace) -> int:
    if args.queue == "outbox":
        rows = list_dead_letter_outbox_entries(limit=args.limit)
        for row in rows:
            print(
                f"id={row.id} event={row.event_type} attempts={row.attempts}/{row.max_attempts} "
                f"processed_at={row.processed_at} error={row.last_error}"
            )
        return len(rows)

    rows = list_dead_letter_conversion_jobs(limit=args.limit)
    for row in rows:
        print(
            f"id={row.id} attachment_id={row.attachment_id} attempts={row.attempts}/{row.max_attempts} "
            f"finished_at={row.finished_at} error={row.last_error}"
        )
    return len(rows)


def _run_requeue(args: argparse.Namespace) -> bool:
    if args.queue == "outbox":
        return requeue_dead_letter_outbox_entry(
            args.id,
            reset_attempts=args.reset_attempts,
        )

    return requeue_dead_letter_conversion_job(
        args.id,
        force=bool(args.force),
        reset_attempts=args.reset_attempts,
    )


def main() -> None:
    args = parse_args()
    init_db()

    if args.command == "list":
        count = _run_list(args)
        print(f"total={count}")
        return

    success = _run_requeue(args)
    print("requeued=1" if success else "requeued=0")


if __name__ == "__main__":
    main()
