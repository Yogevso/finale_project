# Diagrams Workspace

Architecture and workflow diagrams for the Documentation Platform.

Part of the Intel Documentation Platform repository. Use this directory for platform and phase-level visual references, not for normative API or deployment instructions.

## Scope

- Platform-level workflow and sequence references.
- Endpoint-level phase packs (`P0` through `P7`).
- Traceability artifacts that map diagrams to code.

## Core Files

- `ROLE_LEGEND.md`: shared role definitions used by all diagrams.
- `01_PLATFORM_WORKFLOW.md`: platform-wide role workflow map.
- `02_PLATFORM_SEQUENCE.md`: end-to-end role-centric sequence view.
- `03_AUTH_RBAC_WORKFLOW.md`: auth, tenant context, and RBAC deep dive.
- `04_CONTENT_LIFECYCLE_WORKFLOW.md`: author/review/publish lifecycle deep dive.
- `05_CUSTOMER_PUBLIC_CONSUMPTION_SEQUENCE.md`: customer/public distribution and feedback loop.
- `06_DETAILED_LOGIC_AND_EXECUTION_PLAN.md`: decision rules and execution details.
- `SOURCE_MAPPING.md`: code paths used as diagram sources.

## Phase Packs

See [phases/README.md](./phases/README.md) for phase-level artifacts.

## Maintenance Notes

- Update phase `TRACEABILITY.md` files when route, handler, or workflow ownership changes.
- Keep role naming aligned with `ROLE_LEGEND.md` and docs/context ownership artifacts.

## Related Docs

- [Root README](../README.md)
- [Phase Packs](./phases/README.md)
- [Architecture](../docs/ARCHITECTURE.md)
