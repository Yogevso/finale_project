"""Tests for FastAPI app factory and router registry object model."""

from __future__ import annotations

from fastapi import APIRouter

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
