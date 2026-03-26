from __future__ import annotations

import argparse

from scripts import reindex_assistant_rag


def test_run_reindex_rebuilds_and_closes_session(monkeypatch):
    calls: dict[str, object] = {}

    class _StubSession:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    session = _StubSession()

    class _StubIndexer:
        async def ensure_ready(self):
            calls["ready"] = True

        async def reindex_all(self, db):
            calls["db"] = db
            return {"documents_indexed": 3, "total_chunks": 9}

        def get_status(self):
            raise AssertionError("status path should not run")

    monkeypatch.setattr(reindex_assistant_rag, "SessionLocal", lambda: session)
    monkeypatch.setattr(reindex_assistant_rag, "DocumentIndexer", lambda: _StubIndexer())
    monkeypatch.setattr(reindex_assistant_rag, "init_db", lambda: calls.setdefault("init_db", True))

    stats = reindex_assistant_rag.run_reindex()

    assert stats == {"documents_indexed": 3, "total_chunks": 9}
    assert calls["init_db"] is True
    assert calls["ready"] is True
    assert calls["db"] is session
    assert session.closed is True


def test_run_reindex_status_only_skips_rebuild(monkeypatch):
    calls = {"status": 0}

    class _StubSession:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    session = _StubSession()

    class _StubIndexer:
        async def ensure_ready(self):
            raise AssertionError("ready check should not run")

        async def reindex_all(self, db):
            raise AssertionError("rebuild path should not run")

        def get_status(self):
            calls["status"] += 1
            return {"status": "ready", "total_chunks": 42}

    monkeypatch.setattr(reindex_assistant_rag, "SessionLocal", lambda: session)
    monkeypatch.setattr(reindex_assistant_rag, "DocumentIndexer", lambda: _StubIndexer())
    monkeypatch.setattr(reindex_assistant_rag, "init_db", lambda: calls.setdefault("init_db", 0) or None)

    stats = reindex_assistant_rag.run_reindex(status_only=True)

    assert stats == {"status": "ready", "total_chunks": 42}
    assert calls["init_db"] == 0
    assert calls["status"] == 1
    assert session.closed is True


def test_main_prints_json(monkeypatch, capsys):
    monkeypatch.setattr(
        reindex_assistant_rag,
        "parse_args",
        lambda: argparse.Namespace(status_only=True),
    )
    monkeypatch.setattr(
        reindex_assistant_rag,
        "run_reindex",
        lambda *, status_only=False: {"status": "ready", "total_chunks": 42},
    )

    exit_code = reindex_assistant_rag.main()

    assert exit_code == 0
    output = capsys.readouterr().out
    assert '"status": "ready"' in output
    assert '"total_chunks": 42' in output
