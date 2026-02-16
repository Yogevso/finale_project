# Traceability Master Matrix

This file provides a cross-phase, side-by-side traceability view for `P0` to `P7`.

- Per-phase detail source: each phase `TRACEABILITY.md`
- Endpoint source: each phase `SEQUENCE.md`
- Use-case source: each phase `USE_CASE.md`
- Gap/backlog source: each phase `ADDITIONS.md`

## 1) Phase Comparison Matrix

| Phase | Domain | Primary Actors | Regular UC Count | Edge Case Count | Endpoint Families | Primary Guard Patterns | Primary Risk Theme | Detail |
|---|---|---|---:|---:|---|---|---|---|
| `P0` | Access and Identity | System Admin, Admin, Manager, Invitee, Authenticated User | 8 | 8 | Invitations, auth, sessions | Role hierarchy, token validity, password checks, tenant scope | Account takeover and token replay | `P0_ACCESS_IDENTITY/TRACEABILITY.md` |
| `P1` | Governance and Setup | System Admin, Admin, Manager, Auditor | 7 | 7 | RBAC, settings, tenants, companies, users | System-admin gates, role hierarchy, tenant scope, constraints | Misconfiguration and privilege drift | `P1_GOVERNANCE_SETUP/TRACEABILITY.md` |
| `P2` | Authoring and Assembly | Editor, Manager, Admin, Internal Collaborator | 7 | 7 | Documents, versions, attachments, comments, assignments | Editor/internal guards, immutability states, permission checks | Content integrity and unsafe uploads | `P2_AUTHORING_ASSEMBLY/TRACEABILITY.md` |
| `P3` | Real-Time Collaboration | Editor, Viewer, Customer, Collab Server | 8 | 7 | Collab token, state, sessions, activity, snapshots, WS | Read/write permission checks, token-doc binding, session ownership | State loss, stale sessions, write abuse | `P3_COLLABORATION/TRACEABILITY.md` |
| `P4` | Review and Approval | Submitter, Reviewer, Notification/Audit services | 6 | 7 | Review submit/queue/approve/reject/cancel/history | Pending-state checks, no self-approval, stale-version checks | Decision races and workflow inconsistency | `P4_REVIEW_APPROVAL/TRACEABILITY.md` |
| `P5` | Publish and Release | Publisher, Editor, Notification/Audit services | 5 | 7 | Version inspect/publish/mutate/delete | Publish-role checks, approved-review requirement, immutability | Bad release and rollback weakness | `P5_PUBLISH_RELEASE/TRACEABILITY.md` |
| `P6` | Distribution and Consumption | Public User, Customer, Internal Viewer | 6 | 7 | Public, portal, viewer, attachments, search | Visibility filters, assignment checks, active-status checks | Data leakage and delivery abuse | `P6_DISTRIBUTION_CONSUMPTION/TRACEABILITY.md` |
| `P7` | Feedback, Analytics, Audit | Customer, Manager, Admin, System Admin, Any User | 8 | 7 | Feedback, notifications, analytics, exports | Role gates, contributor visibility, current-user scoping | Data quality, export security, abuse | `P7_FEEDBACK_ANALYTICS_AUDIT/TRACEABILITY.md` |

## 2) Regular Use-Case Coverage Matrix

Legend:
- `UC#` = covered use case in that phase
- `N/A` = capability not part of that phase

| Capability | `P0` | `P1` | `P2` | `P3` | `P4` | `P5` | `P6` | `P7` |
|---|---|---|---|---|---|---|---|---|
| Identity bootstrap (invite/accept) | `UC1-UC4` | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| Session management | `UC5-UC8` | N/A | N/A | `UC4`, `UC8` | N/A | N/A | N/A | N/A |
| Governance policy/settings | N/A | `UC1-UC3` | N/A | N/A | N/A | N/A | N/A | N/A |
| Org/tenant administration | N/A | `UC4-UC6` | N/A | N/A | N/A | N/A | N/A | N/A |
| Authoring and version drafting | N/A | N/A | `UC1-UC3` | N/A | N/A | `UC1` | N/A | N/A |
| Attachments and content artifacts | N/A | N/A | `UC4` | N/A | N/A | N/A | `UC5` | N/A |
| Comment and collaboration interactions | N/A | N/A | `UC5-UC6` | `UC1-UC7` | N/A | N/A | `UC6` | N/A |
| Formal review workflow | N/A | N/A | N/A | N/A | `UC1-UC6` | N/A | N/A | N/A |
| Release publication | N/A | N/A | N/A | N/A | N/A | `UC2-UC5` | N/A | N/A |
| Distribution channels | N/A | N/A | N/A | N/A | N/A | N/A | `UC1-UC6` | N/A |
| Feedback lifecycle | N/A | N/A | N/A | N/A | N/A | N/A | N/A | `UC1-UC4` |
| Notification lifecycle | N/A | N/A | N/A | N/A | N/A | `UC4` | N/A | `UC5` |
| Analytics and export | N/A | N/A | N/A | N/A | N/A | N/A | N/A | `UC6-UC8`, `UC7` |

## 3) Edge-Case Control Matrix

Legend:
- `EX#` = explicitly covered edge case in that phase traceability
- `Gap` = marked as improvement candidate in additions

| Control Theme | `P0` | `P1` | `P2` | `P3` | `P4` | `P5` | `P6` | `P7` |
|---|---|---|---|---|---|---|---|---|
| Unauthorized/role escalation actions | `EX2` | `EX2`, `EX3` | `EX5`, `EX6` | `EX2`, `EX4` | `EX2`, `EX5` | `EX7` | `EX1` | `EX2`, `EX4` |
| Cross-tenant leakage risk | `EX8` | `EX2` | `EX6` | `EX4` | `EX5` | `Gap` | `EX3` | `EX7` |
| Duplicate/race condition risk | `Gap` | `EX5` | `EX1` | `EX3` | `EX4` | `EX2`, `EX3` | `EX4` | `EX6` |
| Invalid or stale token/state risk | `EX1`, `EX5` | `EX1` | `EX2` | `EX1`, `EX4` | `EX3` | `EX1` | `EX5` | `EX5` |
| Abuse and rate-limit pressure | `EX4` | `Gap` | `EX3` | `EX5`, `EX7` | `Gap` | `Gap` | `EX4`, `EX7` | `EX1` |
| Data integrity/partial-write risk | `Gap` | `EX7` | `EX4`, `EX7` | `EX3` | `EX7` | `EX3` | `EX6` | `EX5` |
| Notification/reporting reliability risk | `Gap` | `Gap` | `Gap` | `Gap` | `EX7` | `EX5` | `Gap` | `EX3`, `EX6` |

## 4) Cross-Phase Additions Backlog (High Priority)

| Workstream | Phase(s) | Priority | Source File | Target Outcome |
|---|---|---|---|---|
| Identity hardening (rate limits, token rotation, step-up auth) | `P0` | High | `P0_ACCESS_IDENTITY/ADDITIONS.md` | Reduce account takeover and replay risk. |
| Governance safety rails (rollback, dry-run, dual approval) | `P1` | High | `P1_GOVERNANCE_SETUP/ADDITIONS.md` | Prevent policy/config lockouts and misconfig incidents. |
| Content safety and integrity (schema validation, malware scan, atomic writes) | `P2` | High | `P2_AUTHORING_ASSEMBLY/ADDITIONS.md` | Improve authoring reliability and security. |
| Collaboration resilience (heartbeat, revoke protocol, durable state retry) | `P3` | High | `P3_COLLABORATION/ADDITIONS.md` | Prevent stale sessions and state-loss events. |
| Review robustness (multi-stage, quorum, idempotent decisions) | `P4` | High | `P4_REVIEW_APPROVAL/ADDITIONS.md` | Increase review quality and transition consistency. |
| Release safety (idempotent publish, rollback path, post-release checks) | `P5` | High | `P5_PUBLISH_RELEASE/ADDITIONS.md` | Lower bad-release blast radius. |
| Delivery protection (signed URLs, ACL re-check, tenant-safe caching) | `P6` | High | `P6_DISTRIBUTION_CONSUMPTION/ADDITIONS.md` | Reduce leakage and abuse in content delivery. |
| Feedback/analytics governance (anti-spam, event schema governance, secure exports) | `P7` | High | `P7_FEEDBACK_ANALYTICS_AUDIT/ADDITIONS.md` | Improve trust and security of reporting pipelines. |

## 5) Suggested Implementation Sequence

1. `P0`, `P1` security and governance controls first (foundation risk reduction).
2. `P2`, `P3` integrity and collaboration reliability next (authoring/runtime correctness).
3. `P4`, `P5` workflow/release safety controls after core correctness is stable.
4. `P6`, `P7` scale, delivery, and analytics hardening as production traffic expands.
