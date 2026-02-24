"""Startup DB initialization flow tests."""

from app import db as db_module


def test_init_db_prefers_managed_migrations(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(db_module, "_run_managed_migrations", lambda: True)
    monkeypatch.setattr(
        db_module,
        "_bootstrap_schema_from_metadata",
        lambda: calls.append("bootstrap"),
    )

    def fake_lightweight(*, skip_versions_semantic_migration: bool = False) -> None:
        calls.append(f"lightweight:{skip_versions_semantic_migration}")

    monkeypatch.setattr(db_module, "_run_lightweight_migrations", fake_lightweight)

    db_module.init_db()

    assert calls == ["lightweight:True"]


def test_init_db_bootstraps_metadata_when_managed_migrations_unavailable(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(db_module, "_run_managed_migrations", lambda: False)
    monkeypatch.setattr(
        db_module,
        "_bootstrap_schema_from_metadata",
        lambda: calls.append("bootstrap"),
    )

    def fake_lightweight(*, skip_versions_semantic_migration: bool = False) -> None:
        calls.append(f"lightweight:{skip_versions_semantic_migration}")

    monkeypatch.setattr(db_module, "_run_lightweight_migrations", fake_lightweight)

    db_module.init_db()

    assert calls == ["bootstrap", "lightweight:False"]
