#!/usr/bin/env python3
"""Fetch and summarize review comments for the PR of the current branch."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from typing import Any

QUERY = """\
query(
  $owner: String!,
  $repo: String!,
  $number: Int!,
  $commentsCursor: String,
  $reviewsCursor: String,
  $threadsCursor: String
) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      number
      url
      title
      state
      comments(first: 100, after: $commentsCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          body
          createdAt
          updatedAt
          author { login }
        }
      }
      reviews(first: 100, after: $reviewsCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          state
          body
          submittedAt
          author { login }
        }
      }
      reviewThreads(first: 100, after: $threadsCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          originalLine
          comments(first: 100) {
            nodes {
              id
              body
              createdAt
              updatedAt
              author { login }
            }
          }
        }
      }
    }
  }
}
"""


def _run(cmd: list[str], stdin: str | None = None) -> str:
    process = subprocess.run(cmd, input=stdin, capture_output=True, text=True)
    if process.returncode != 0:
        cmd_text = " ".join(cmd)
        raise RuntimeError(f"Command failed: {cmd_text}\n{process.stderr.strip()}")
    return process.stdout


def _run_json(cmd: list[str], stdin: str | None = None) -> dict[str, Any]:
    output = _run(cmd, stdin=stdin)
    try:
        return json.loads(output)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Failed to parse JSON output: {error}") from error


def _ensure_gh_ready() -> None:
    if shutil.which("gh") is None:
        raise RuntimeError("GitHub CLI is not installed. Install `gh` first.")
    try:
        _run(["gh", "auth", "status"])
    except RuntimeError as error:
        raise RuntimeError(
            "GitHub CLI is not authenticated. Run `gh auth login` and retry."
        ) from error


def _current_pr() -> tuple[str, str, int]:
    pr = _run_json(["gh", "pr", "view", "--json", "number,headRepositoryOwner,headRepository"])
    owner = pr["headRepositoryOwner"]["login"]
    repo = pr["headRepository"]["name"]
    number = int(pr["number"])
    return owner, repo, number


def _graphql_page(
    owner: str,
    repo: str,
    number: int,
    comments_cursor: str | None,
    reviews_cursor: str | None,
    threads_cursor: str | None,
) -> dict[str, Any]:
    cmd = [
        "gh",
        "api",
        "graphql",
        "-F",
        "query=@-",
        "-F",
        f"owner={owner}",
        "-F",
        f"repo={repo}",
        "-F",
        f"number={number}",
    ]
    if comments_cursor:
        cmd += ["-F", f"commentsCursor={comments_cursor}"]
    if reviews_cursor:
        cmd += ["-F", f"reviewsCursor={reviews_cursor}"]
    if threads_cursor:
        cmd += ["-F", f"threadsCursor={threads_cursor}"]
    return _run_json(cmd, stdin=QUERY)


def _fetch_all(owner: str, repo: str, number: int) -> dict[str, Any]:
    comments: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    review_threads: list[dict[str, Any]] = []
    comments_cursor: str | None = None
    reviews_cursor: str | None = None
    threads_cursor: str | None = None
    pr_meta: dict[str, Any] | None = None

    while True:
        payload = _graphql_page(
            owner=owner,
            repo=repo,
            number=number,
            comments_cursor=comments_cursor,
            reviews_cursor=reviews_cursor,
            threads_cursor=threads_cursor,
        )
        if payload.get("errors"):
            raise RuntimeError(f"GitHub GraphQL error: {json.dumps(payload['errors'], indent=2)}")

        pr = payload["data"]["repository"]["pullRequest"]
        if pr_meta is None:
            pr_meta = {
                "number": pr["number"],
                "url": pr["url"],
                "title": pr["title"],
                "state": pr["state"],
                "owner": owner,
                "repo": repo,
            }

        pr_comments = pr["comments"]
        pr_reviews = pr["reviews"]
        pr_threads = pr["reviewThreads"]
        comments.extend(pr_comments.get("nodes") or [])
        reviews.extend(pr_reviews.get("nodes") or [])
        review_threads.extend(pr_threads.get("nodes") or [])

        comments_cursor = (
            pr_comments["pageInfo"]["endCursor"] if pr_comments["pageInfo"]["hasNextPage"] else None
        )
        reviews_cursor = (
            pr_reviews["pageInfo"]["endCursor"] if pr_reviews["pageInfo"]["hasNextPage"] else None
        )
        threads_cursor = (
            pr_threads["pageInfo"]["endCursor"] if pr_threads["pageInfo"]["hasNextPage"] else None
        )
        if not (comments_cursor or reviews_cursor or threads_cursor):
            break

    if pr_meta is None:
        raise RuntimeError("Failed to read PR metadata.")

    return {
        "pull_request": pr_meta,
        "conversation_comments": comments,
        "reviews": reviews,
        "review_threads": review_threads,
    }


def _one_line(text: str, max_len: int = 140) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 3] + "..."


def _render_summary(payload: dict[str, Any], include_resolved: bool) -> str:
    pr = payload["pull_request"]
    threads = payload["review_threads"]
    if not include_resolved:
        threads = [thread for thread in threads if not thread.get("isResolved") and not thread.get("isOutdated")]

    lines = [
        f"PR #{pr['number']}: {pr['title']}",
        pr["url"],
        "",
    ]

    if not threads:
        lines.append("No unresolved review threads.")
    else:
        lines.append("Unresolved review threads:")
        for index, thread in enumerate(threads, start=1):
            comments = (thread.get("comments") or {}).get("nodes") or []
            latest = comments[-1] if comments else {}
            author = (latest.get("author") or {}).get("login", "unknown")
            body = _one_line(latest.get("body", ""))
            path = thread.get("path") or "unknown"
            line = thread.get("line") or thread.get("originalLine") or "?"
            lines.append(f"{index}. {path}:{line} - @{author} - {body}")

    change_requests = [
        review
        for review in payload["reviews"]
        if review.get("state") == "CHANGES_REQUESTED" and (review.get("body") or "").strip()
    ]
    if change_requests:
        lines.extend(["", "Change-request review summaries:"])
        for index, review in enumerate(change_requests, start=1):
            author = (review.get("author") or {}).get("login", "unknown")
            lines.append(f"{index}. @{author}: {_one_line(review['body'])}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        choices=("summary", "json"),
        default="summary",
        help="Output format (default: summary).",
    )
    parser.add_argument(
        "--include-resolved",
        action="store_true",
        help="Include resolved/outdated threads in summary mode.",
    )
    args = parser.parse_args()

    try:
        _ensure_gh_ready()
        owner, repo, number = _current_pr()
        payload = _fetch_all(owner=owner, repo=repo, number=number)
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(payload, indent=2))
        return 0

    print(_render_summary(payload, include_resolved=args.include_resolved))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
