"""Portal CLI entry point — Click command group."""

from __future__ import annotations

import click
from rich.console import Console

from .auth import ensure_authenticated, login as do_login, logout as do_logout
from .chat import interactive_chat, one_shot_chat
from .commands import (
    delete_conversation_cmd,
    list_conversations,
    show_status,
    show_tools,
)
from .config import CLIConfig

console = Console()


@click.group()
@click.version_option(package_name="portal-cli")
@click.pass_context
def cli(ctx: click.Context):
    """Portal CLI — AI Assistant and Admin Tools."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = CLIConfig.load()


# ── Auth ──────────────────────────────────────────────────────────


@cli.command()
@click.option("--server", "-s", default=None, help="Server URL (e.g. http://localhost:8000)")
@click.option("--username", "-u", prompt=True, help="Username")
@click.option("--password", "-p", prompt=True, hide_input=True, help="Password")
@click.pass_context
def login(ctx: click.Context, server: str | None, username: str, password: str):
    """Authenticate with the Portal backend."""
    config: CLIConfig = ctx.obj["config"]
    if server:
        config.server_url = server
    if do_login(config, username, password):
        console.print(f"[green]✓[/green] Logged in as [bold]{username}[/bold]")
    else:
        raise SystemExit(1)


@cli.command()
@click.pass_context
def logout(ctx: click.Context):
    """Clear stored authentication token."""
    config: CLIConfig = ctx.obj["config"]
    do_logout(config)
    console.print("[dim]Logged out.[/dim]")


# ── Chat ──────────────────────────────────────────────────────────


@cli.command()
@click.argument("message", required=False)
@click.option("--continue", "-c", "continue_conv", is_flag=True, help="Continue last conversation")
@click.pass_context
def chat(ctx: click.Context, message: str | None, continue_conv: bool):
    """Chat with the AI Assistant.

    Without arguments, starts an interactive REPL.
    With a MESSAGE argument, sends a single question and exits.
    """
    config: CLIConfig = ctx.obj["config"]
    if not ensure_authenticated(config):
        raise SystemExit(1)

    if message:
        cid = config.last_conversation_id if continue_conv else None
        one_shot_chat(config, message, conversation_id=cid)
    else:
        interactive_chat(config, continue_conv=continue_conv)


# ── Direct commands ───────────────────────────────────────────────


@cli.command()
@click.pass_context
def status(ctx: click.Context):
    """Show AI assistant and system health."""
    config: CLIConfig = ctx.obj["config"]
    if not ensure_authenticated(config):
        raise SystemExit(1)
    show_status(config)


@cli.command()
@click.pass_context
def tools(ctx: click.Context):
    """List available AI tools for your role."""
    config: CLIConfig = ctx.obj["config"]
    if not ensure_authenticated(config):
        raise SystemExit(1)
    show_tools(config)


@cli.group(name="conversations")
def conversations_group():
    """Manage chat conversations."""


@conversations_group.command(name="list")
@click.pass_context
def conversations_list(ctx: click.Context):
    """List recent conversations."""
    config: CLIConfig = ctx.obj["config"]
    if not ensure_authenticated(config):
        raise SystemExit(1)
    list_conversations(config)


@conversations_group.command(name="delete")
@click.argument("conversation_id", type=int)
@click.pass_context
def conversations_delete(ctx: click.Context, conversation_id: int):
    """Delete a conversation by ID."""
    config: CLIConfig = ctx.obj["config"]
    if not ensure_authenticated(config):
        raise SystemExit(1)
    delete_conversation_cmd(config, conversation_id)


if __name__ == "__main__":
    cli()
