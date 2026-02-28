"""Plugin registry lifecycle tests."""

from __future__ import annotations

import pytest
from fastapi.responses import StreamingResponse

from app.conversion.models import DocumentConversionRequest
from app.plugins.converters import DocumentConverterPluginRegistry
from app.plugins.exporters import AnalyticsExportPluginRegistry
from app.plugins.notifications import NotificationChannelPluginRegistry


class _ConverterPlugin:
    def __init__(self, name: str, *, mime_prefix: str, html: str):
        self.name = name
        self._mime_prefix = mime_prefix
        self._html = html

    def supports(self, request: DocumentConversionRequest) -> bool:
        return request.normalized_mime_type.startswith(self._mime_prefix)

    def convert_to_html(self, request: DocumentConversionRequest) -> str:
        _ = request
        return self._html


class _ExporterPlugin:
    def __init__(self, format_name: str, supported_reports: tuple[str, ...]):
        self.format_name = format_name
        self.supported_reports = supported_reports

    def export(self, **_kwargs) -> StreamingResponse:
        return StreamingResponse(iter(["ok"]), media_type="text/plain")


class _RecordingChannel:
    async def deliver(self, _message) -> bool:
        return True


class _ChannelPlugin:
    def __init__(self, name: str):
        self.name = name

    def build_channel(self) -> _RecordingChannel:
        return _RecordingChannel()


def test_document_converter_registry_load_validate_and_select():
    registry = DocumentConverterPluginRegistry(
        plugins=[
            _ConverterPlugin("text", mime_prefix="text/", html="<p>text</p>"),
            _ConverterPlugin("app", mime_prefix="application/", html="<p>app</p>"),
        ]
    )

    request = DocumentConversionRequest(
        content=b"{}",
        mime_type="application/json",
        filename="sample.json",
    )
    selected = registry.select(request)

    assert selected is not None
    assert selected.name == "app"
    assert selected.convert_to_html(request) == "<p>app</p>"


def test_document_converter_registry_rejects_duplicate_names():
    registry = DocumentConverterPluginRegistry()
    registry.register(_ConverterPlugin("text", mime_prefix="text/", html="<p>a</p>"))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(_ConverterPlugin("text", mime_prefix="text/", html="<p>b</p>"))


def test_analytics_export_plugin_registry_resolve_and_validation():
    registry = AnalyticsExportPluginRegistry(
        plugins=[_ExporterPlugin("csv", supported_reports=("overview",))]
    )

    resolved = registry.resolve("csv")
    assert resolved.supported_reports == ("overview",)

    with pytest.raises(KeyError, match="No analytics exporter plugin"):
        registry.resolve("pdf")


def test_analytics_export_plugin_registry_rejects_invalid_plugins():
    registry = AnalyticsExportPluginRegistry()

    with pytest.raises(ValueError, match="must declare supported reports"):
        registry.register(_ExporterPlugin("csv", supported_reports=()))


def test_notification_channel_plugin_registry_builds_channels_by_name():
    registry = NotificationChannelPluginRegistry(
        plugins=[
            _ChannelPlugin("email"),
            _ChannelPlugin("webhook"),
        ]
    )

    channels = registry.build_channels(["webhook"])

    assert len(channels) == 1
    assert isinstance(channels[0], _RecordingChannel)


def test_notification_channel_plugin_registry_rejects_duplicate_names():
    registry = NotificationChannelPluginRegistry()
    registry.register(_ChannelPlugin("email"))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(_ChannelPlugin("email"))
