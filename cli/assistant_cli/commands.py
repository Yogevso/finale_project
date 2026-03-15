"""Direct CLI commands — status, tools, conversations."""

from __future__ import annotations

import asyncio

from rich.console import Console
from rich.table import Table

from .client import PortalClient
from .config import CLIConfig

console = Console()


def show_status(config: CLIConfig) -> None:
    """Display assistant and system health."""
    client = PortalClient(config)

    async def _run():
        try:
            health = await client.get_assistant_health()
            status = health.get("status", "unknown")
            model = health.get("model", "?")
            ollama = "✓ healthy" if health.get("ollama_healthy") else "✗ unhealthy"

            color = "green" if status == "ready" else "red"
            console.print(f"\n[bold]AI Assistant Status:[/bold] [{color}]{status}[/{color}]")
            console.print(f"  Model:  {model}")
            console.print(f"  Ollama: {ollama}")
            console.print(f"  Server: {config.server_url}")
            if config.username:
                console.print(f"  User:   {config.username}")
            console.print()
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")

    asyncio.run(_run())


def show_tools(config: CLIConfig) -> None:
    """List available AI tools for the current user."""
    client = PortalClient(config)

    async def _run():
        try:
            tools = await client.get_available_tools()
            table = Table(title=f"Available Tools ({len(tools)})")
            table.add_column("Name", style="cyan")
            table.add_column("Description")
            for t in tools:
                table.add_row(t["name"], t["description"])
            console.print(table)
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")

    asyncio.run(_run())


def list_conversations(config: CLIConfig) -> None:
    """List recent conversations."""
    client = PortalClient(config)

    async def _run():
        try:
            convs = await client.list_conversations(limit=30)
            if not convs:
                console.print("[dim]No conversations yet.[/dim]")
                return
            table = Table(title=f"Conversations ({len(convs)})")
            table.add_column("ID", style="cyan", justify="right")
            table.add_column("Title")
            table.add_column("Messages", justify="center")
            table.add_column("Updated")
            for c in convs:
                table.add_row(
                    str(c["id"]),
                    c["title"],
                    str(c.get("message_count", "?")),
                    c.get("updated_at", "")[:19],
                )
            console.print(table)
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")

    asyncio.run(_run())


def delete_conversation_cmd(config: CLIConfig, conversation_id: int) -> None:
    """Delete a specific conversation."""
    client = PortalClient(config)

    async def _run():
        try:
            ok = await client.delete_conversation(conversation_id)
            if ok:
                console.print(f"[green]Conversation #{conversation_id} deleted.[/green]")
            else:
                console.print(f"[red]Conversation #{conversation_id} not found.[/red]")
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")

    asyncio.run(_run())
