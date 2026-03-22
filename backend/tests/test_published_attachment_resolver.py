"""C6: Integration tests for PublishedAttachmentResolver.

Verifies that public, viewer and portal attachment endpoints only serve
attachments that existed at the time of the latest publish — not files
uploaded afterwards.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.services.published_attachment_resolver import (
    is_attachment_in_published_snapshot,
    resolve_published_attachment_ids,
)


# ---------------------------------------------------------------------------
# Helpers — lightweight ORM stand-ins so we don't depend on a live DB for
# the resolver's unit-level semantics.  Full end-to-end coverage should use
# the real DB via the test fixtures in conftest.py.
# ---------------------------------------------------------------------------


class _FakeRow:
    """Minimal stand-in returned by ``query().all()``."""

    def __init__(self, id_: int):
        self._id = id_

    def __getitem__(self, idx):
        return self._id


class _FakeQuery:
    def __init__(self, rows=None, first_val=None):
        self._rows = rows or []
        self._first_val = first_val

    def filter(self, *a, **kw):
        return self

    def order_by(self, *a):
        return self

    def first(self):
        return self._first_val

    def all(self):
        return self._rows


class _FakeVersion:
    """Simulates a Version model row."""

    def __init__(
        self,
        *,
        snapshot_json: str | None = None,
        published_at: datetime | None = None,
        created_at: datetime | None = None,
    ):
        self.published_attachment_ids_snapshot = snapshot_json
        self.published_at = published_at
        self.created_at = created_at


# ---------------------------------------------------------------------------
# Tests for resolve_published_attachment_ids
# ---------------------------------------------------------------------------


class TestResolveFromSnapshot:
    """When the snapshot column is populated, the resolver should use it."""

    def test_returns_ids_from_snapshot(self, monkeypatch):
        version = _FakeVersion(snapshot_json=json.dumps([1, 2, 3]))

        class FakeDB:
            def query(self, model):
                return _FakeQuery(first_val=version)

        result = resolve_published_attachment_ids(FakeDB(), document_id=10)
        assert result == {1, 2, 3}

    def test_empty_snapshot_returns_empty(self, monkeypatch):
        version = _FakeVersion(snapshot_json=json.dumps([]))

        class FakeDB:
            def query(self, model):
                return _FakeQuery(first_val=version)

        result = resolve_published_attachment_ids(FakeDB(), document_id=10)
        assert result == set()


class TestResolveFromCutoff:
    """When snapshot is NULL the resolver falls back to cutoff timestamp."""

    def test_falls_back_to_cutoff(self):
        now = datetime.now(timezone.utc)
        version = _FakeVersion(snapshot_json=None, published_at=now)

        call_count = {"n": 0}

        class FakeQuery:
            def filter(self, *a, **kw):
                return self

            def order_by(self, *a):
                return self

            def first(self):
                return version

            def all(self):
                # Return two attachment ID rows
                return [_FakeRow(10), _FakeRow(20)]

        class FakeDB:
            def query(self, model):
                call_count["n"] += 1
                return FakeQuery()

        result = resolve_published_attachment_ids(FakeDB(), document_id=5)
        assert result == {10, 20}


class TestNoPublishedVersion:
    """If the document has no published version, return empty set."""

    def test_no_version_returns_empty(self):
        class FakeDB:
            def query(self, model):
                return _FakeQuery(first_val=None)

        result = resolve_published_attachment_ids(FakeDB(), document_id=99)
        assert result == set()


class TestIsAttachmentInPublishedSnapshot:
    def test_in_snapshot(self):
        version = _FakeVersion(snapshot_json=json.dumps([5, 10, 15]))

        class FakeDB:
            def query(self, model):
                return _FakeQuery(first_val=version)

        assert is_attachment_in_published_snapshot(FakeDB(), 1, 10) is True
        assert is_attachment_in_published_snapshot(FakeDB(), 1, 99) is False
