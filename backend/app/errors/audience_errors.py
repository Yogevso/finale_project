"""Audience-domain error catalog locked for contract compatibility checks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final


class AudienceErrorCode(str, Enum):
    AUDIENCE_001 = "missing_company_assignment"
    AUDIENCE_002 = "invalid_company_set"
    AUDIENCE_003 = "invalid_visibility"
    AUDIENCE_004 = "visibility_reason_required"
    AUDIENCE_005 = "if_match_required"
    AUDIENCE_006 = "if_match_conflict"
    AUDIENCE_007 = "company_not_assigned"
    AUDIENCE_008 = "inactive_company_assignment"
    AUDIENCE_009 = "stale_company_assignment"
    AUDIENCE_010 = "tenant_scope_violation"
    AUDIENCE_011 = "schema_version_unsupported"
    AUDIENCE_012 = "audience_alert_rule_invalid"
    AUDIENCE_013 = "audience_alert_rule_not_found"
    AUDIENCE_014 = "audit_signature_missing"
    AUDIENCE_015 = "audit_signature_invalid"
    AUDIENCE_016 = "audience_snapshot_missing"
    AUDIENCE_017 = "audience_restore_invalid"
    AUDIENCE_018 = "public_transition_risk"
    AUDIENCE_019 = "assignment_churn_threshold_exceeded"
    AUDIENCE_020 = "audit_export_invalid_format"


@dataclass(frozen=True)
class AudienceErrorDefinition:
    id: str
    slug: str
    description: str
    http_status: int


AUDIENCE_ERROR_CATALOG: Final[tuple[AudienceErrorDefinition, ...]] = (
    AudienceErrorDefinition(
        id="AUDIENCE_001",
        slug=AudienceErrorCode.AUDIENCE_001.value,
        description="Company visibility requires at least one assigned company.",
        http_status=400,
    ),
    AudienceErrorDefinition(
        id="AUDIENCE_002",
        slug=AudienceErrorCode.AUDIENCE_002.value,
        description="Company assignment payload is invalid.",
        http_status=400,
    ),
    AudienceErrorDefinition(
        id="AUDIENCE_003",
        slug=AudienceErrorCode.AUDIENCE_003.value,
        description="Visibility value is invalid.",
        http_status=400,
    ),
    AudienceErrorDefinition(
        id="AUDIENCE_004",
        slug=AudienceErrorCode.AUDIENCE_004.value,
        description="Visibility changes require a non-empty reason.",
        http_status=400,
    ),
    AudienceErrorDefinition(
        id="AUDIENCE_005",
        slug=AudienceErrorCode.AUDIENCE_005.value,
        description="If-Match precondition header is required.",
        http_status=428,
    ),
    AudienceErrorDefinition(
        id="AUDIENCE_006",
        slug=AudienceErrorCode.AUDIENCE_006.value,
        description="If-Match token is stale and conflicts with current resource version.",
        http_status=409,
    ),
    AudienceErrorDefinition(
        id="AUDIENCE_007",
        slug=AudienceErrorCode.AUDIENCE_007.value,
        description="Requested company is not currently assigned to the document.",
        http_status=400,
    ),
    AudienceErrorDefinition(
        id="AUDIENCE_008",
        slug=AudienceErrorCode.AUDIENCE_008.value,
        description="Inactive companies cannot be assigned to documents.",
        http_status=400,
    ),
    AudienceErrorDefinition(
        id="AUDIENCE_009",
        slug=AudienceErrorCode.AUDIENCE_009.value,
        description="Assigned company became stale/deactivated.",
        http_status=400,
    ),
    AudienceErrorDefinition(
        id="AUDIENCE_010",
        slug=AudienceErrorCode.AUDIENCE_010.value,
        description="User cannot access audience data outside tenant scope.",
        http_status=403,
    ),
    AudienceErrorDefinition(
        id="AUDIENCE_011",
        slug=AudienceErrorCode.AUDIENCE_011.value,
        description="Requested audience schema version is unsupported.",
        http_status=400,
    ),
    AudienceErrorDefinition(
        id="AUDIENCE_012",
        slug=AudienceErrorCode.AUDIENCE_012.value,
        description="Audience alert rule payload is invalid.",
        http_status=400,
    ),
    AudienceErrorDefinition(
        id="AUDIENCE_013",
        slug=AudienceErrorCode.AUDIENCE_013.value,
        description="Audience alert rule was not found.",
        http_status=404,
    ),
    AudienceErrorDefinition(
        id="AUDIENCE_014",
        slug=AudienceErrorCode.AUDIENCE_014.value,
        description="Expected audit signature is missing.",
        http_status=400,
    ),
    AudienceErrorDefinition(
        id="AUDIENCE_015",
        slug=AudienceErrorCode.AUDIENCE_015.value,
        description="Audit signature verification failed.",
        http_status=400,
    ),
    AudienceErrorDefinition(
        id="AUDIENCE_016",
        slug=AudienceErrorCode.AUDIENCE_016.value,
        description="No audience snapshot exists for this operation.",
        http_status=400,
    ),
    AudienceErrorDefinition(
        id="AUDIENCE_017",
        slug=AudienceErrorCode.AUDIENCE_017.value,
        description="Audience snapshot could not be restored safely.",
        http_status=400,
    ),
    AudienceErrorDefinition(
        id="AUDIENCE_018",
        slug=AudienceErrorCode.AUDIENCE_018.value,
        description="Public exposure transition requires explicit governance context.",
        http_status=400,
    ),
    AudienceErrorDefinition(
        id="AUDIENCE_019",
        slug=AudienceErrorCode.AUDIENCE_019.value,
        description="Assignment churn exceeds configured governance threshold.",
        http_status=400,
    ),
    AudienceErrorDefinition(
        id="AUDIENCE_020",
        slug=AudienceErrorCode.AUDIENCE_020.value,
        description="Requested audit export format is unsupported.",
        http_status=400,
    ),
)


AUDIENCE_ERROR_BY_SLUG: Final[dict[str, AudienceErrorDefinition]] = {
    item.slug: item for item in AUDIENCE_ERROR_CATALOG
}

