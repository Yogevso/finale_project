"""Legacy management controller wrapper."""

from __future__ import annotations

from app.application.contexts.users.api import UsersContextAPI


class UsersController(UsersContextAPI):
    """Legacy HTTP-facing adapter retained for compatibility."""
