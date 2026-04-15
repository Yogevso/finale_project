"""Managed (Alembic) migration bootstrap helpers."""

from __future__ import annotations

import logging
from pathlib import Path


def run_managed_migrations(
    *,
    database_url: str,
    db_module_path: Path,
    logger: logging.Logger,
    section_name: str | None = None,
) -> bool:
    """Run Alembic migrations when project scaffolding is present.

    Args:
        section_name: Optional named ini section (e.g. ``"analytics"``).
                      When *None*, uses the default ``[alembic]`` section.
    """
    alembic_ini = db_module_path.resolve().parents[1] / "alembic.ini"
    alembic_dir = db_module_path.resolve().parents[1] / "alembic"
    if not alembic_ini.exists() or not alembic_dir.exists():
        return False

    try:
        from alembic import command
        from alembic.config import Config
    except Exception as exc:  # policy: DEGRADED — missing Alembic keeps lightweight migrations available; pragma: no cover - import path is environment dependent.
        logger.warning("Alembic import unavailable; using lightweight migrations only: %s", exc)
        return False

    config = Config(str(alembic_ini), ini_section=section_name or "alembic")
    if section_name:
        # Named sections store their own script_location
        script_loc = config.get_main_option("script_location")
        if script_loc:
            config.set_main_option("script_location", str(alembic_dir.parent / script_loc))
    else:
        config.set_main_option("script_location", str(alembic_dir))
    config.set_main_option("sqlalchemy.url", database_url)

    try:
        command.upgrade(config, "head")
        return True
    except (
        Exception
    ) as exc:  # policy: DEGRADED — managed migrations can fall back to lightweight bootstrap
        logger.warning(
            "Managed migration upgrade failed; continuing with lightweight fallback: %s",
            exc,
        )
        return False
