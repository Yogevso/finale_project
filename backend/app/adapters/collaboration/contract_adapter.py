"""Anti-corruption adapter for collaboration token/state contracts."""

from __future__ import annotations

from collections.abc import Sequence


class CollaborationContractAdapter:
    """Normalizes collaboration payload fields exchanged with external runtimes."""

    _allowed_permissions = {"read", "write"}

    def coerce_document_id(self, document_id: int | str) -> int:
        """Normalize external document identifiers to positive integer IDs."""
        if isinstance(document_id, int):
            normalized = document_id
        else:
            stripped = str(document_id).strip()
            if not stripped.isdigit():
                raise ValueError("Document ID must be a positive integer")
            normalized = int(stripped)

        if normalized < 1:
            raise ValueError("Document ID must be a positive integer")
        return normalized

    def normalize_permissions(self, permissions: Sequence[str]) -> list[str]:
        """Normalize external permission payloads to canonical read/write order."""
        normalized_permissions: set[str] = set()
        for raw_permission in permissions:
            permission = str(raw_permission).strip().lower()
            if permission not in self._allowed_permissions:
                continue
            normalized_permissions.add(permission)

        if "write" in normalized_permissions:
            normalized_permissions.add("read")

        return [permission for permission in ("read", "write") if permission in normalized_permissions]

    def permissions_from_access(self, *, can_view: bool, can_edit: bool) -> list[str]:
        """Build canonical external permissions from domain access decisions."""
        if can_edit:
            return ["read", "write"]
        if can_view:
            return ["read"]
        return []
