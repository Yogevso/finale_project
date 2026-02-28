"""Tenant-isolation attack harness coverage for protected endpoints."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from tests.tenant_isolation.harness import (
    TenantAttackPattern,
    TenantIsolationAttackHarness,
    build_attack_cases,
)


@dataclass(frozen=True, slots=True)
class _EndpointDefinition:
    name: str
    method: str
    path_template: str
    actor: str
    expected_statuses: tuple[int, ...]
    json_template: dict[str, object] | None = None
    content: bytes | None = None
    content_type: str | None = None


READ_ENDPOINT_DEFINITIONS: tuple[_EndpointDefinition, ...] = (
    _EndpointDefinition(
        name="document_detail",
        method="GET",
        path_template="/api/v1/documents/{document_id}",
        actor="attacker_editor",
        expected_statuses=(404,),
    ),
    _EndpointDefinition(
        name="document_assigned_companies",
        method="GET",
        path_template="/api/v1/documents/{document_id}/assigned-companies",
        actor="attacker_editor",
        expected_statuses=(404,),
    ),
    _EndpointDefinition(
        name="bff_document_detail_bundle",
        method="GET",
        path_template="/api/v1/bff/documents/{document_id}/detail-page",
        actor="attacker_editor",
        expected_statuses=(404,),
    ),
    _EndpointDefinition(
        name="review_detail",
        method="GET",
        path_template="/api/v1/reviews/{review_id}",
        actor="attacker_manager",
        expected_statuses=(404,),
    ),
    _EndpointDefinition(
        name="collaboration_state",
        method="GET",
        path_template="/api/v1/collaboration/documents/{document_id}/state",
        actor="attacker_editor",
        expected_statuses=(403,),
    ),
    _EndpointDefinition(
        name="collaboration_status",
        method="GET",
        path_template="/api/v1/collaboration/documents/{document_id}/status",
        actor="attacker_editor",
        expected_statuses=(403,),
    ),
    _EndpointDefinition(
        name="collaboration_snapshots_list",
        method="GET",
        path_template="/api/v1/collaboration/documents/{document_id}/snapshots",
        actor="attacker_editor",
        expected_statuses=(403,),
    ),
)


WRITE_ENDPOINT_DEFINITIONS: tuple[_EndpointDefinition, ...] = (
    _EndpointDefinition(
        name="document_update",
        method="PUT",
        path_template="/api/v1/documents/{document_id}",
        actor="attacker_editor",
        expected_statuses=(404,),
        json_template={"description": "cross-tenant update attempt"},
    ),
    _EndpointDefinition(
        name="document_delete",
        method="DELETE",
        path_template="/api/v1/documents/{document_id}",
        actor="attacker_manager",
        expected_statuses=(404,),
    ),
    _EndpointDefinition(
        name="assign_companies",
        method="POST",
        path_template="/api/v1/documents/{document_id}/assign-companies",
        actor="attacker_manager",
        expected_statuses=(404,),
        json_template={"company_ids": ["{owner_tenant_id}"]},
    ),
    _EndpointDefinition(
        name="remove_company_assignment",
        method="DELETE",
        path_template="/api/v1/documents/{document_id}/assign-companies/{owner_tenant_id}",
        actor="attacker_manager",
        expected_statuses=(404,),
    ),
    _EndpointDefinition(
        name="submit_review",
        method="POST",
        path_template="/api/v1/reviews/documents/{document_id}/submit",
        actor="attacker_editor",
        expected_statuses=(404,),
        json_template={"message": "cross-tenant review submit"},
    ),
    _EndpointDefinition(
        name="approve_review",
        method="POST",
        path_template="/api/v1/reviews/{review_id}/approve",
        actor="attacker_manager",
        expected_statuses=(404,),
        json_template={"comments": "cross-tenant approve"},
    ),
    _EndpointDefinition(
        name="collab_token",
        method="POST",
        path_template="/api/v1/auth/collab-token",
        actor="attacker_editor",
        expected_statuses=(403,),
        json_template={"document_id": "{document_id}"},
    ),
    _EndpointDefinition(
        name="collaboration_save_state",
        method="PUT",
        path_template="/api/v1/collaboration/documents/{document_id}/state",
        actor="attacker_editor",
        expected_statuses=(403,),
        content=b"\x01\x02\x03\x04",
        content_type="application/octet-stream",
    ),
    _EndpointDefinition(
        name="collaboration_start_session",
        method="POST",
        path_template="/api/v1/collaboration/sessions/start",
        actor="attacker_editor",
        expected_statuses=(403,),
        json_template={"document_id": "{document_id}"},
    ),
    _EndpointDefinition(
        name="collaboration_log_activity",
        method="POST",
        path_template="/api/v1/collaboration/activity",
        actor="attacker_editor",
        expected_statuses=(403,),
        json_template={
            "document_id": "{document_id}",
            "activity_type": "cursor_moved",
            "details": {"position": 5},
        },
    ),
    _EndpointDefinition(
        name="collaboration_create_snapshot",
        method="POST",
        path_template="/api/v1/collaboration/documents/{document_id}/snapshots",
        actor="attacker_editor",
        expected_statuses=(403,),
        json_template={"name": "cross-tenant snapshot"},
    ),
)


def _generate_attack_patterns(
    *,
    category: str,
    definitions: tuple[_EndpointDefinition, ...],
) -> tuple[TenantAttackPattern, ...]:
    """Generate materializable attack patterns from endpoint definitions."""
    return tuple(
        TenantAttackPattern(
            name=f"{category}.{definition.name}",
            method=definition.method,
            path_template=definition.path_template,
            actor=definition.actor,
            expected_statuses=definition.expected_statuses,
            json_template=definition.json_template,
            content=definition.content,
            content_type=definition.content_type,
        )
        for definition in definitions
    )


ATTACK_PATTERNS: tuple[TenantAttackPattern, ...] = (
    _generate_attack_patterns(category="read", definitions=READ_ENDPOINT_DEFINITIONS)
    + _generate_attack_patterns(category="write", definitions=WRITE_ENDPOINT_DEFINITIONS)
)


@pytest.mark.parametrize("pattern", ATTACK_PATTERNS, ids=[pattern.name for pattern in ATTACK_PATTERNS])
def test_cross_tenant_attack_harness_denies_protected_endpoints(
    client,
    tenant_isolation_scenario,
    tenant_isolation_actor_headers,
    pattern: TenantAttackPattern,
):
    harness = TenantIsolationAttackHarness(
        client=client,
        actor_headers=tenant_isolation_actor_headers,
    )
    [case] = build_attack_cases(tenant_isolation_scenario, [pattern])
    harness.run_case(case)

