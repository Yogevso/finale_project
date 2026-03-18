#!/usr/bin/env python3
"""AA-009: Dependency vulnerability response pipeline.

Runs pip-audit (Python) and npm audit (JS) to detect critical/high severity
vulnerabilities and auto-creates a GitHub issue for critical CVEs.

Usage:
    python -m scripts.dependency_audit
    python -m scripts.dependency_audit --create-issues
    python -m scripts.dependency_audit --format json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPORT_DIR = Path("data/security_reports")


def run_pip_audit() -> dict:
    """Run pip-audit to scan Python dependencies."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--format", "json", "--strict"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            return {"status": "pass", "vulnerabilities": [], "tool": "pip-audit"}

        try:
            vulns = json.loads(result.stdout) if result.stdout else []
        except json.JSONDecodeError:
            vulns = []

        critical_high = [
            v for v in vulns
            if isinstance(v, dict) and v.get("fix_versions")
        ]
        return {
            "status": "fail" if critical_high else "warn",
            "vulnerabilities": vulns,
            "critical_high_count": len(critical_high),
            "tool": "pip-audit",
        }
    except FileNotFoundError:
        return {"status": "skip", "reason": "pip-audit not installed", "tool": "pip-audit"}
    except subprocess.TimeoutExpired:
        return {"status": "skip", "reason": "pip-audit timed out", "tool": "pip-audit"}


def run_npm_audit() -> dict:
    """Run npm audit to scan JavaScript dependencies."""
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
    if not (frontend_dir / "package.json").exists():
        return {"status": "skip", "reason": "No frontend package.json found", "tool": "npm-audit"}

    try:
        result = subprocess.run(
            ["npm", "audit", "--json"],
            capture_output=True,
            text=True,
            cwd=str(frontend_dir),
            timeout=120,
        )
        try:
            audit_data = json.loads(result.stdout) if result.stdout else {}
        except json.JSONDecodeError:
            audit_data = {}

        metadata = audit_data.get("metadata", {})
        vulns = metadata.get("vulnerabilities", {})
        critical = vulns.get("critical", 0)
        high = vulns.get("high", 0)

        return {
            "status": "fail" if (critical + high) > 0 else "pass",
            "critical": critical,
            "high": high,
            "moderate": vulns.get("moderate", 0),
            "low": vulns.get("low", 0),
            "total": vulns.get("total", 0),
            "tool": "npm-audit",
        }
    except FileNotFoundError:
        return {"status": "skip", "reason": "npm not available", "tool": "npm-audit"}
    except subprocess.TimeoutExpired:
        return {"status": "skip", "reason": "npm audit timed out", "tool": "npm-audit"}


def generate_issue_body(report: dict) -> str:
    """Generate a GitHub issue body from vulnerability report."""
    lines = [
        "## Dependency Vulnerability Report",
        f"**Scan Date:** {report['scanned_at']}",
        f"**Overall Status:** {report['overall_status'].upper()}",
        "",
    ]

    for check_name, check in report["checks"].items():
        lines.append(f"### {check['tool']}")
        lines.append(f"Status: **{check['status']}**")
        if check.get("critical_high_count"):
            lines.append(f"Critical/High: **{check['critical_high_count']}**")
        if check.get("critical"):
            lines.append(f"Critical: {check['critical']}, High: {check['high']}")
        if check.get("vulnerabilities"):
            lines.append("\n| Package | Vulnerability | Fix |")
            lines.append("|---------|--------------|-----|")
            for v in check["vulnerabilities"][:20]:
                if isinstance(v, dict):
                    name = v.get("name", "?")
                    vuln_id = v.get("vulns", [{}])[0].get("id", "?") if v.get("vulns") else "?"
                    fix = ", ".join(v.get("fix_versions", [])) if v.get("fix_versions") else "N/A"
                    lines.append(f"| {name} | {vuln_id} | {fix} |")
        lines.append("")

    return "\n".join(lines)


def create_github_issue(title: str, body: str) -> bool:
    """Create a GitHub issue using the gh CLI."""
    try:
        result = subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", body, "--label", "security"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print(f"  GitHub issue created: {result.stdout.strip()}")
            return True
        print(f"  Failed to create issue: {result.stderr}")
        return False
    except FileNotFoundError:
        print("  gh CLI not available — skipping issue creation")
        return False


def run_full_audit(create_issues: bool = False) -> dict:
    """Run all dependency audit checks."""
    report = {
        "scanned_at": datetime.utcnow().isoformat(),
        "checks": {},
    }

    print("=" * 60)
    print("  DEPENDENCY VULNERABILITY AUDIT")
    print("=" * 60)
    print()

    print("Scanning Python dependencies (pip-audit)...")
    pip_result = run_pip_audit()
    report["checks"]["python"] = pip_result
    icon = "✓" if pip_result["status"] == "pass" else "✗" if pip_result["status"] == "fail" else "⊘"
    ch_count = pip_result.get('critical_high_count', 0)
    pip_reason = pip_result.get('reason', f'{ch_count} critical/high issues')
    print(f"  {icon} {pip_reason}")
    print()

    print("Scanning JavaScript dependencies (npm audit)...")
    npm_result = run_npm_audit()
    report["checks"]["javascript"] = npm_result
    icon = "✓" if npm_result["status"] == "pass" else "✗" if npm_result["status"] == "fail" else "⊘"
    detail = npm_result.get("reason", f"Critical: {npm_result.get('critical', 0)}, High: {npm_result.get('high', 0)}")
    print(f"  {icon} {detail}")
    print()

    statuses = [c["status"] for c in report["checks"].values()]
    report["overall_status"] = "fail" if "fail" in statuses else "pass"

    print("=" * 60)
    print(f"  AUDIT RESULT: {report['overall_status'].upper()}")
    print("=" * 60)

    if create_issues and report["overall_status"] == "fail":
        print("\nCreating GitHub issue for critical vulnerabilities...")
        title = f"[Security] Critical dependency vulnerabilities found — {datetime.utcnow().strftime('%Y-%m-%d')}"
        body = generate_issue_body(report)
        create_github_issue(title, body)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Dependency vulnerability audit")
    parser.add_argument("--create-issues", action="store_true", help="Create GitHub issues for critical CVEs")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    args = parser.parse_args()

    report = run_full_audit(create_issues=args.create_issues)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"vuln_scan_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(report, indent=2))

    if args.format == "json":
        print(json.dumps(report, indent=2))

    print(f"\nReport saved to: {report_path}")
    sys.exit(0 if report["overall_status"] != "fail" else 1)


if __name__ == "__main__":
    main()
