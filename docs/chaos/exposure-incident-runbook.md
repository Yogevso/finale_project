# Exposure Incident Runbook

## Purpose
This runbook handles incidents where a document is accidentally exposed to a broader audience (for example `public` instead of `internal`/`company`).

## Scope
Use this when any document visibility or company-assignment misconfiguration can expose restricted content.

## Severity Guide
- `SEV-1`: Sensitive data publicly reachable or large-scale tenant exposure.
- `SEV-2`: Limited audience leak within authenticated users.
- `SEV-3`: Near-miss, blocked before real user access.

## Roles
- `Incident Commander (IC)`: owns timeline and decisions.
- `Ops Lead`: executes containment and rollback.
- `App Engineer`: validates state + applies code/config mitigations.
- `Comms Lead`: internal/external communication updates.

## Detection Triggers
- Unexpected increase in public document traffic.
- Alert from analytics/audit review about visibility flip.
- Customer report of unauthorized document access.
- Dead-letter or warning events tied to audience enforcement bypass.

## Immediate Actions (0-15 minutes)
1. Open an incident channel and assign `IC`.
2. Freeze risky changes:
- Disable release pipeline for document/audience changes.
- Enable strict audience enforcement (`FEATURE_FLAG_COMPANY_AUDIENCE_ENFORCEMENT=true`) if currently disabled.
3. Identify exposed document IDs and exposure window start time.
4. Capture evidence before mutation:
- Current document metadata (`status`, `visibility`, `row_version`).
- Assigned company IDs.
- Latest published version and audience snapshot.
- Relevant audit log rows and request IDs.

## Containment (15-30 minutes)
1. Restrict audience immediately:
- Set document visibility to `internal` or `company` as appropriate.
- Remove unintended company assignments.
2. If state is uncertain, restore audience from a known-good published snapshot:
- `POST /api/v1/documents/{document_id}/versions/{version_id}/restore-audience`
3. If exposure cannot be safely corrected quickly, archive document:
- Use document archive flow to remove active/public access.
4. Confirm containment:
- Public endpoint returns `404`/not visible.
- Unauthorized tenant/user can no longer access document.

## Verification Checklist
- Document no longer appears in `/api/v1/public/*` responses.
- Audience preview shows intended visibility and company scope.
- Search/portal results no longer expose the document to unauthorized users.
- Audit log includes containment actions and actor IDs.
- Affected caches/projections are invalidated and refreshed.

## Communication
- Internal update every 30 minutes until containment confirmed.
- Customer notice required for `SEV-1`/regulated data exposure.
- Include:
- Impacted document IDs.
- Exposure window (`start`, `end`).
- Data classes exposed.
- Containment timestamp and next update ETA.

## Forensics and Evidence
Preserve:
- Audit logs (visibility changes, assignment changes, publishes).
- API access logs for affected document IDs.
- Feature flag states during incident.
- Outbox/dead-letter records linked to audience events.
- Timeline of operator actions.

## Recovery
1. Re-enable normal operations only after:
- Access checks pass for all affected documents.
- No lingering public exposure in smoke checks.
- IC signs off.
2. Add temporary monitoring for 24h:
- visibility-change rate
- public endpoint access spikes
- publish warnings tied to audience bypass/safe-mode

## Post-Incident (within 48 hours)
1. Run blameless postmortem with root cause and corrective actions.
2. Add/adjust tests for the missed failure mode.
3. Tighten guardrails:
- Keep kill-switch defaults documented.
- Restrict who can change visibility to `public`.
- Require reason capture for exposure-prone transitions.
4. Update this runbook with concrete lessons learned.

## Quick Command Checklist
- `python -m pytest tests/test_versions.py -k "enforcement or advisory or safe_mode" -x -q --tb=short --basetemp="$PWD\temp\pytest"`
- `python -m pytest tests/tenant_isolation/ -x -q --tb=short --basetemp="$PWD\temp\pytest"`
- `python -m ruff check app/ tests/`
