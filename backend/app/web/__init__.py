"""Web layer package.

HTTP/router composition modules should live here.
"""

from .router_registry import (
    FastAPIRouterRegistry,
    RouterRegistration,
    build_default_router_registry,
    register_routers,
)

__all__ = [
    "FastAPIRouterRegistry",
    "RouterRegistration",
    "build_default_router_registry",
    "register_routers",
]
