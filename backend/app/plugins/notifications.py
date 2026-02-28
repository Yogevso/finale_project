"""Plugin registry for notification delivery channels."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.domain.ports import EmailPort
from app.infrastructure.composition import get_email_port
from app.notifications.channels import EmailNotificationChannel, NotificationChannel


class NotificationChannelPlugin(Protocol):
    """Plugin contract for producing notification channels."""

    name: str

    def build_channel(self) -> NotificationChannel:
        """Create channel instance for dispatcher usage."""


class NotificationChannelPluginRegistry:
    """Registry for notification channel plugins."""

    def __init__(self, plugins: Sequence[NotificationChannelPlugin] | None = None) -> None:
        self._plugins: dict[str, NotificationChannelPlugin] = {}
        self.load(plugins or [])

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._plugins.keys())

    def load(self, plugins: Sequence[NotificationChannelPlugin]) -> None:
        for plugin in plugins:
            self.register(plugin)

    def register(self, plugin: NotificationChannelPlugin) -> None:
        name = (plugin.name or "").strip().lower()
        if not name:
            raise ValueError("Notification channel plugin name is required")
        if name in self._plugins:
            raise ValueError(f"Notification channel plugin '{name}' is already registered")
        self._plugins[name] = plugin

    def build_channels(self, names: Sequence[str] | None = None) -> list[NotificationChannel]:
        selected_names = [name.strip().lower() for name in names] if names else list(self._plugins)
        channels: list[NotificationChannel] = []
        for name in selected_names:
            plugin = self._plugins.get(name)
            if not plugin:
                raise KeyError(f"Notification channel plugin '{name}' is not registered")
            channels.append(plugin.build_channel())
        return channels


class EmailNotificationChannelPlugin:
    """Default email notification channel plugin."""

    name = "email"

    def __init__(self, email_port: EmailPort | None = None) -> None:
        self._email_port = email_port

    def build_channel(self) -> NotificationChannel:
        return EmailNotificationChannel(self._email_port or get_email_port())


def build_default_notification_channel_plugin_registry() -> NotificationChannelPluginRegistry:
    """Load built-in notification channels."""
    return NotificationChannelPluginRegistry(plugins=[EmailNotificationChannelPlugin()])


_default_notification_channel_plugin_registry = build_default_notification_channel_plugin_registry()


def get_notification_channel_plugin_registry() -> NotificationChannelPluginRegistry:
    """Resolve shared notification-channel registry singleton."""
    return _default_notification_channel_plugin_registry
