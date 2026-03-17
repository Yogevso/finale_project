#!/usr/bin/env python3
"""
AA-016: Public API Version Sunset Tooling

Scheduled job that:
1. Reads docs/deprecations.json for deprecated endpoints
2. Sends 30-day advance warnings for approaching sunset dates
3. Reports endpoints past their sunset date that should be removed

Usage:
    python -m scripts.api_sunset_check
    python -m scripts.api_sunset_check --warn-days 30
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEPRECATIONS_PATH = Path(__file__).resolve().parents[2] / "docs" / "deprecations.json"
DEPRECATIONS_MD_PATH = Path(__file__).resolve().parents[2] / "docs" / "deprecations.md"
DEFAULT_WARN_DAYS = 30


def load_deprecations() -> list[dict]:
    """Load machine-readable deprecation registry."""
    if not DEPRECATIONS_PATH.exists():
        logger.info("No deprecations.json found — nothing to check.")
        return []
    with DEPRECATIONS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def check_sunset_dates(warn_days: int = DEFAULT_WARN_DAYS) -> dict:
    """Check all deprecation entries against current date.

    Returns dict with:
      - past_sunset: entries whose sunset date has passed (should remove)
      - approaching: entries within warn_days of sunset (send warning)
      - active: entries still in deprecation window
      - total: total count
    """
    now = datetime.now(timezone.utc)
    warn_threshold = now + timedelta(days=warn_days)

    deprecations = load_deprecations()
    result = {
        "checked_at": now.isoformat(),
        "warn_days": warn_days,
        "past_sunset": [],
        "approaching": [],
        "active": [],
        "total": len(deprecations),
    }

    for dep in deprecations:
        sunset_str = dep.get("sunset_date", "")
        if not sunset_str:
            continue

        try:
            sunset_dt = datetime.strptime(sunset_str, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            logger.warning("Invalid sunset_date '%s' for %s", sunset_str, dep.get("id"))
            continue

        entry = {
            "id": dep.get("id"),
            "path_prefix": dep.get("path_prefix"),
            "sunset_date": sunset_str,
            "replacement": dep.get("replacement"),
            "stage": dep.get("stage"),
            "days_until_sunset": (sunset_dt - now).days,
        }

        if sunset_dt <= now:
            entry["action"] = "REMOVE — sunset date has passed"
            result["past_sunset"].append(entry)
        elif sunset_dt <= warn_threshold:
            entry["action"] = f"WARN — sunset in {entry['days_until_sunset']} days"
            result["approaching"].append(entry)
        else:
            entry["action"] = "OK — still in deprecation window"
            result["active"].append(entry)

    return result


def print_report(report: dict) -> None:
    """Print human-readable sunset check report."""
    print("\n" + "=" * 60)
    print("API Version Sunset Check Report")
    print(f"Checked at: {report['checked_at']}")
    print(f"Warning threshold: {report['warn_days']} days")
    print(f"Total deprecations: {report['total']}")
    print("=" * 60)

    if report["past_sunset"]:
        print(f"\n🔴 PAST SUNSET ({len(report['past_sunset'])} endpoints):")
        for e in report["past_sunset"]:
            print(f"  {e['id']}: {e['path_prefix']}")
            print(f"    Sunset: {e['sunset_date']} ({abs(e['days_until_sunset'])} days ago)")
            print(f"    Replace with: {e.get('replacement', 'N/A')}")

    if report["approaching"]:
        print(f"\n🟡 APPROACHING SUNSET ({len(report['approaching'])} endpoints):")
        for e in report["approaching"]:
            print(f"  {e['id']}: {e['path_prefix']}")
            print(f"    Sunset: {e['sunset_date']} (in {e['days_until_sunset']} days)")
            print(f"    Replace with: {e.get('replacement', 'N/A')}")

    if report["active"]:
        print(f"\n🟢 ACTIVE DEPRECATIONS ({len(report['active'])} endpoints):")
        for e in report["active"]:
            print(f"  {e['id']}: {e['path_prefix']}")
            print(f"    Sunset: {e['sunset_date']} (in {e['days_until_sunset']} days)")

    if not report["past_sunset"] and not report["approaching"]:
        print("\n✅ No endpoints require immediate action.")

    print()


def main() -> None:
    warn_days = DEFAULT_WARN_DAYS
    if "--warn-days" in sys.argv:
        idx = sys.argv.index("--warn-days")
        if idx + 1 < len(sys.argv):
            warn_days = int(sys.argv[idx + 1])

    report = check_sunset_dates(warn_days)
    print_report(report)

    # Exit with error code if any endpoints are past sunset
    if report["past_sunset"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
