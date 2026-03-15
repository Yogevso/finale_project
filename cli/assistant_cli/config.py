"""CLI configuration management — stored at ~/.portal-cli/config.json."""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".portal-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"


class CLIConfig:
    """Persistent configuration for the Portal CLI."""

    def __init__(
        self,
        server_url: str = "http://localhost:8000",
        api_prefix: str = "/api/v1",
        access_token: str | None = None,
        refresh_token: str | None = None,
        username: str | None = None,
        last_conversation_id: int | None = None,
    ):
        self.server_url = server_url
        self.api_prefix = api_prefix
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.username = username
        self.last_conversation_id = last_conversation_id

    @property
    def base_url(self) -> str:
        return f"{self.server_url.rstrip('/')}{self.api_prefix}"

    # ── Persistence ───────────────────────────────────────────────

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "server_url": self.server_url,
            "api_prefix": self.api_prefix,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "username": self.username,
            "last_conversation_id": self.last_conversation_id,
        }
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls) -> CLIConfig:
        if not CONFIG_FILE.exists():
            return cls()
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return cls(**{k: v for k, v in data.items() if k in cls.__init__.__code__.co_varnames})
        except (json.JSONDecodeError, TypeError):
            return cls()

    def clear_token(self) -> None:
        self.access_token = None
        self.refresh_token = None
        self.save()
