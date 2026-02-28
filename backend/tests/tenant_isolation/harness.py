"""Reusable tenant-isolation attack harness for endpoint regression tests."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from fastapi.testclient import TestClient

from app.models import Document, ReviewRequest, Tenant, User

_PLACEHOLDER_PATTERN = re.compile(r"^\{([a-zA-Z_][a-zA-Z0-9_]*)\}$")


@dataclass(frozen=True, slots=True)
class TenantIsolationScenario:
    """Tenant-isolation seed data shared across attack cases."""

    owner_tenant: Tenant
    attacker_tenant: Tenant
    owner_user: User
    attacker_editor: User
    attacker_manager: User
    attacker_editor_password: str
    attacker_manager_password: str
    document: Document
    review: ReviewRequest

    def template_context(self) -> dict[str, Any]:
        """Values available for path/body template interpolation."""
        return {
            "document_id": self.document.id,
            "review_id": self.review.id,
            "owner_tenant_id": self.owner_tenant.id,
            "attacker_tenant_id": self.attacker_tenant.id,
        }


@dataclass(frozen=True, slots=True)
class TenantAttackPattern:
    """Template describing one cross-tenant attack attempt."""

    name: str
    method: str
    path_template: str
    actor: str
    expected_statuses: tuple[int, ...]
    json_template: Mapping[str, Any] | None = None
    query_template: Mapping[str, Any] | None = None
    content: bytes | None = None
    content_type: str | None = None


@dataclass(frozen=True, slots=True)
class TenantAttackCase:
    """Materialized attack case resolved against one scenario."""

    name: str
    method: str
    path: str
    actor: str
    expected_statuses: tuple[int, ...]
    json_body: Mapping[str, Any] | None = None
    query_params: Mapping[str, Any] | None = None
    content: bytes | None = None
    content_type: str | None = None


def _render_template_value(value: Any, context: Mapping[str, Any]) -> Any:
    if isinstance(value, str):
        full_placeholder = _PLACEHOLDER_PATTERN.fullmatch(value)
        if full_placeholder:
            key = full_placeholder.group(1)
            return context[key]
        return value.format(**context)
    if isinstance(value, list):
        return [_render_template_value(item, context) for item in value]
    if isinstance(value, tuple):
        return tuple(_render_template_value(item, context) for item in value)
    if isinstance(value, Mapping):
        return {key: _render_template_value(item, context) for key, item in value.items()}
    return value


def build_attack_cases(
    scenario: TenantIsolationScenario,
    patterns: Iterable[TenantAttackPattern],
) -> list[TenantAttackCase]:
    """Resolve template patterns into executable attack cases."""
    context = scenario.template_context()
    cases: list[TenantAttackCase] = []
    for pattern in patterns:
        path = pattern.path_template.format(**context)
        json_body = (
            _render_template_value(pattern.json_template, context)
            if pattern.json_template is not None
            else None
        )
        query_params = (
            _render_template_value(pattern.query_template, context)
            if pattern.query_template is not None
            else None
        )
        cases.append(
            TenantAttackCase(
                name=pattern.name,
                method=pattern.method.upper(),
                path=path,
                actor=pattern.actor,
                expected_statuses=pattern.expected_statuses,
                json_body=json_body,
                query_params=query_params,
                content=pattern.content,
                content_type=pattern.content_type,
            )
        )
    return cases


class TenantIsolationAttackHarness:
    """Executes tenant-attack cases against a FastAPI TestClient."""

    def __init__(
        self,
        *,
        client: TestClient,
        actor_headers: Mapping[str, Mapping[str, str]],
    ) -> None:
        self._client = client
        self._actor_headers = actor_headers

    def run_case(self, case: TenantAttackCase) -> None:
        if case.actor not in self._actor_headers:
            raise AssertionError(f"Missing auth headers for actor '{case.actor}'")

        headers = dict(self._actor_headers[case.actor])
        if case.content_type:
            headers["Content-Type"] = case.content_type

        request_kwargs: dict[str, Any] = {"headers": headers}
        if case.json_body is not None:
            request_kwargs["json"] = case.json_body
        if case.query_params is not None:
            request_kwargs["params"] = case.query_params
        if case.content is not None:
            request_kwargs["content"] = case.content

        response = self._client.request(case.method, case.path, **request_kwargs)
        if response.status_code not in case.expected_statuses:
            body_preview = response.text[:300]
            raise AssertionError(
                f"[{case.name}] {case.method} {case.path} as {case.actor} expected "
                f"{case.expected_statuses}, got {response.status_code}. Response: {body_preview}"
            )

    def run_all(self, cases: Iterable[TenantAttackCase]) -> None:
        for case in cases:
            self.run_case(case)

