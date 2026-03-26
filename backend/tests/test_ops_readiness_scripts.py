"""Regression coverage for production-readiness helper scripts."""

from __future__ import annotations

from pathlib import Path

from scripts import backup_restore_drill, disaster_recovery_validation, rotate_secrets


def test_resolve_database_target_supports_postgres_and_sqlite():
    postgres = backup_restore_drill.resolve_database_target(
        "postgresql://portal:secret@db:5432/portal"
    )
    sqlite = backup_restore_drill.resolve_database_target(
        "sqlite:///./data/portal.db"
    )

    assert postgres.dialect == "postgresql"
    assert postgres.database_name == "portal"
    assert sqlite.dialect == "sqlite"
    assert sqlite.sqlite_path == Path("data/portal.db")


def test_create_backup_uses_pg_dump_for_postgres(monkeypatch, tmp_path):
    target = backup_restore_drill.resolve_database_target(
        "postgresql://portal:secret@db:5432/portal"
    )
    recorded: dict[str, object] = {}

    def fake_run(command, *, env=None):
        recorded["command"] = command
        recorded["env"] = env
        backup_path = Path(command[command.index("--file") + 1])
        backup_path.write_bytes(b"pg-dump")
        return None

    monkeypatch.setattr(backup_restore_drill, "run_command", fake_run)

    backup_path = backup_restore_drill.create_backup(target, tmp_path)

    assert backup_path.suffix == ".dump"
    assert recorded["command"][0] == "pg_dump"
    assert "--dbname" in recorded["command"]
    assert "portal" in recorded["command"]
    assert recorded["env"]["PGPASSWORD"] == "secret"


def test_check_backup_recency_uses_postgres_backup_pattern(tmp_path):
    backup_path = tmp_path / "portal_backup_20260326_120000.dump"
    backup_path.write_bytes(b"pg-dump")

    result = disaster_recovery_validation.check_backup_recency(
        database_url="postgresql://portal:secret@db:5432/portal",
        backup_dir=tmp_path,
    )

    assert result["status"] == "pass"
    assert result["backend"] == "postgresql"
    assert result["latest_backup"].endswith(".dump")


def test_rotate_jwt_secret_instructions_include_secret_key_old(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "c" * 48)

    result = rotate_secrets.rotate_jwt_secret()

    assert result["type"] == "jwt"
    assert any("SECRET_KEY_OLD=" in instruction for instruction in result["instructions"])
    assert any("collab-server" in instruction for instruction in result["instructions"])
