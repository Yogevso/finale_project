"""Rebuild the assistant semantic-search vector index.

Usage:
    python scripts/reindex_assistant_rag.py
    python scripts/reindex_assistant_rag.py --status-only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.assistant.rag.indexer import DocumentIndexer
from app.db import SessionLocal, init_db

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild the assistant RAG vector index")
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="Print current vector-store stats without rebuilding the index",
    )
    return parser.parse_args()


def run_reindex(*, status_only: bool = False) -> dict[str, Any]:
    init_db()
    db = SessionLocal()
    try:
        indexer = DocumentIndexer()
        if status_only:
            return indexer.get_status()
        asyncio.run(indexer.ensure_ready())
        return asyncio.run(indexer.reindex_all(db))
    finally:
        db.close()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()

    try:
        stats = run_reindex(status_only=args.status_only)
    except Exception:
        logger.exception("Assistant RAG reindex failed")
        return 1

    print(json.dumps(stats, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
