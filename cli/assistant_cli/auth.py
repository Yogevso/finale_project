"""Authentication helpers — login, logout, token management."""

from __future__ import annotations

import httpx
from rich.console import Console

from .config import CLIConfig

console = Console()


def login(config: CLIConfig, username: str, password: str) -> bool:
    """Authenticate against the backend and store the JWT."""
    try:
        r = httpx.post(
            f"{config.base_url}/auth/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        if r.status_code == 200:
            body = r.json()
            config.access_token = body.get("access_token")
            config.refresh_token = body.get("refresh_token")
            config.username = username
            config.save()
            return True
        console.print(f"[red]Login failed:[/red] {r.text}")
        return False
    except httpx.ConnectError:
        console.print(f"[red]Cannot reach server at {config.server_url}[/red]")
        return False


def logout(config: CLIConfig) -> None:
    config.clear_token()


def ensure_authenticated(config: CLIConfig) -> bool:
    """Return True if we have a stored token, else prompt."""
    if config.access_token:
        return True
    console.print("[yellow]Not logged in.[/yellow] Use [bold]portal-cli login[/bold] first.")
    return False
