"""Tests for FastAPI app factory and router registry object model."""

from __future__ import annotations

import warnings

from fastapi import APIRouter
from fastapi.testclient import TestClient

from app import app_factory as app_factory_module
from app.app_factory import FastAPIAppFactory
from app.web.router_registry import (
    FastAPIRouterRegistry,
    RouterRegistration,
    build_default_router_registry,
)


def test_default_router_registry_returns_declarative_entries():
    registry = build_default_router_registry()
    registrations = registry.registrations()

    assert registrations
    assert isinstance(registrations[0], RouterRegistration)
    assert registrations[0].tags == ("Health",)
    assert any(entry.tags == ("Authentication",) for entry in registrations)


def test_app_factory_allows_custom_router_registry():
    probe_router = APIRouter()

    @probe_router.get("/factory-probe")
    async def factory_probe():
        return {"ok": True}

    class ProbeRegistry(FastAPIRouterRegistry):
        def __init__(self) -> None:
            super().__init__(api_prefix="/api/v1")

        def registrations(self) -> tuple[RouterRegistration, ...]:
            return (RouterRegistration(probe_router),)

    app = FastAPIAppFactory(router_registry=ProbeRegistry()).create()
    route_paths = {route.path for route in app.routes}

    assert "/factory-probe" in route_paths
    assert "/" in route_paths


def test_app_factory_startup_initializes_runtime_once(monkeypatch):
    class _StubSession:
        def close(self) -> None:
            return None

    init_calls: list[str] = []
    publish_calls: list[str] = []

    monkeypatch.setattr(app_factory_module, "init_db", lambda: init_calls.append("init"))
    monkeypatch.setattr(app_factory_module, "SessionLocal", lambda: _StubSession())

    from app.services.rbac_service import RbacService

    monkeypatch.setattr(
        RbacService,
        "publish_policies",
        staticmethod(lambda _db: publish_calls.append("publish")),
    )

    app = FastAPIAppFactory().create()

    with TestClient(app):
        pass
    with TestClient(app):
        pass

    assert init_calls == ["init"]
    assert publish_calls == ["publish", "publish"]


def test_app_factory_does_not_emit_fastapi_on_event_deprecation_warning():
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        app = FastAPIAppFactory().create()
        with TestClient(app):
            pass

    assert not any(
        warning.category is DeprecationWarning and "on_event is deprecated" in str(warning.message)
        for warning in captured
    )
