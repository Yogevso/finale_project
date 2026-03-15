"""Interactive chat REPL with Rich rendering and SSE streaming."""

from __future__ import annotations

import asyncio

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text

from .client import PortalClient
from .config import CLIConfig

console = Console()

REPL_HELP = """\
[bold]REPL commands:[/bold]
  /help    Show this help message
  /new     Start a new conversation
  /tools   List available AI tools
  /history Show recent conversations
  /clear   Clear the screen
  /quit    Exit the chat
"""


async def _stream_chat(
    client: PortalClient,
    message: str,
    conversation_id: int | None,
    config: CLIConfig,
) -> int | None:
    """Send a message and render the streamed response. Returns conversation_id."""
    cid = conversation_id
    accumulated = ""
    spinner_text = ""

    with Live(console=console, refresh_per_second=15, transient=False) as live:
        async for event in client.chat_stream(message, conversation_id):
            etype = event.get("event", "")

            if etype == "conversation_id":
                cid = event["data"]
                config.last_conversation_id = cid
                config.save()

            elif etype == "token":
                accumulated += event["data"]
                live.update(Markdown(accumulated))

            elif etype == "tool_call":
                tc = event["data"]
                name = tc.get("name", "unknown") if isinstance(tc, dict) else str(tc)
                spinner_text = f"🔧  Calling [bold]{name}[/bold]…"
                live.update(Spinner("dots", text=spinner_text, style="cyan"))

            elif etype == "tool_result":
                tr = event["data"] if isinstance(event["data"], dict) else {}
                success = tr.get("success", False)
                name = tr.get("name", "tool")
                if success:
                    console.print(f"  [green]✓[/green] {name} succeeded")
                else:
                    console.print(f"  [red]✗[/red] {name} failed: {tr.get('error', '')}")

            elif etype == "done":
                if accumulated:
                    live.update(Markdown(accumulated))

            elif etype == "error":
                msg = event["data"] if isinstance(event["data"], str) else event["data"].get("message", "Unknown error")
                live.update(Text(f"⚠  {msg}", style="red"))
                break

    console.print()
    return cid


def interactive_chat(config: CLIConfig, continue_conv: bool = False) -> None:
    """Start an interactive chat REPL."""
    client = PortalClient(config)
    cid = config.last_conversation_id if continue_conv else None

    console.print(
        Panel(
            "[bold]Portal Assistant[/bold]  (type [cyan]/help[/cyan] for commands, [cyan]/quit[/cyan] to exit)",
            border_style="sky_blue1",
        )
    )
    if cid:
        console.print(f"[dim]Resuming conversation #{cid}[/dim]\n")

    while True:
        try:
            user_input = console.input("[bold sky_blue1]You:[/bold sky_blue1] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim] 👋")
            break

        if not user_input:
            continue

        # REPL commands
        if user_input.startswith("/"):
            cmd = user_input.lower().split()[0]
            if cmd in ("/quit", "/exit", "/q"):
                console.print("[dim]Goodbye![/dim] 👋")
                break
            elif cmd == "/help":
                console.print(REPL_HELP)
                continue
            elif cmd == "/new":
                cid = None
                console.print("[dim]Starting new conversation.[/dim]\n")
                continue
            elif cmd == "/tools":
                asyncio.run(_show_tools(client))
                continue
            elif cmd == "/history":
                asyncio.run(_show_history(client))
                continue
            elif cmd == "/clear":
                console.clear()
                continue
            else:
                console.print(f"[yellow]Unknown command: {cmd}[/yellow]  (try /help)")
                continue

        # Regular message
        console.print()
        cid = asyncio.run(_stream_chat(client, user_input, cid, config))


def one_shot_chat(config: CLIConfig, message: str, conversation_id: int | None = None) -> None:
    """Send a single message, print the response, and exit."""
    client = PortalClient(config)
    asyncio.run(_stream_chat(client, message, conversation_id, config))


async def _show_tools(client: PortalClient) -> None:
    try:
        tools = await client.get_available_tools()
        console.print(f"\n[bold]Available tools ({len(tools)}):[/bold]")
        for t in tools:
            console.print(f"  [cyan]{t['name']}[/cyan] — {t['description']}")
        console.print()
    except Exception as exc:
        console.print(f"[red]Error loading tools:[/red] {exc}")


async def _show_history(client: PortalClient) -> None:
    try:
        convs = await client.list_conversations(limit=15)
        if not convs:
            console.print("[dim]No conversations yet.[/dim]\n")
            return
        console.print(f"\n[bold]Recent conversations ({len(convs)}):[/bold]")
        for c in convs:
            console.print(
                f"  [cyan]#{c['id']}[/cyan] {c['title']} "
                f"[dim]({c.get('message_count', '?')} msgs)[/dim]"
            )
        console.print()
    except Exception as exc:
        console.print(f"[red]Error loading conversations:[/red] {exc}")
