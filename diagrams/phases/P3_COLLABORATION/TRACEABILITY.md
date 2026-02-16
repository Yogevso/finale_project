# P3: Real-Time Collaboration - Traceability Matrix

## Regular Use Case Mapping

| Use Case ID | Use Case | Endpoint(s) | Rule(s) / Guard(s) | Notes |
|---|---|---|---|---|
| UC1 | Request collaboration token | `POST /auth/collab-token` | Document-specific access checks | Token carries read/write claims. |
| UC2 | Connect to document channel | `ws://<collab-host>:8002/document/{documentId}?token=<collab-jwt>` | Token verification + doc id match | Connection mode becomes read-only or editable. |
| UC3 | Hydrate collaboration state | `GET /collaboration/documents/{id}/state` | Read permission | Loads existing CRDT state when available. |
| UC4 | Start tracked collaboration session | `POST /collaboration/sessions/start` | Read access | Session lifecycle begins with join activity. |
| UC5 | Realtime edit/presence operations | WebSocket updates + `POST /collaboration/activity` | Valid activity types + permission context | Tracks active collaboration signals. |
| UC6 | Persist CRDT state | `PUT /collaboration/documents/{id}/state` | Write permission | Debounced persistence path. |
| UC7 | Manage snapshots | `POST/GET/PATCH/DELETE /collaboration/documents/{id}/snapshots...`, `POST /collaboration/documents/{id}/auto-snapshot` | Read/write by operation + interval/state checks | Supports manual and automated snapshots. |
| UC8 | End session | `POST /collaboration/sessions/end` | Own active session | Logs leave activity and closes session. |

## Extreme and Edge Case Mapping

| Edge ID | Scenario | Endpoint(s) | Current Enforcement | Gap / Additional Control |
|---|---|---|---|---|
| EX1 | Invalid token or document mismatch | `POST /auth/collab-token`, WebSocket connect | Token and doc-id validation | Add detailed reject reason telemetry for incident analysis. |
| EX2 | Read-only collaborator attempts write | `PUT /collaboration/documents/{id}/state` | Write permission required | Add explicit client downgrade signaling (`ADDITIONS.md`). |
| EX3 | Network partition/backpressure on state save | `PUT /collaboration/documents/{id}/state` | Debounced persist flow | Add durable retry queue and backpressure controls (`ADDITIONS.md`). |
| EX4 | Mid-session permission revocation | WebSocket + state save endpoints | Permission evaluated per operation | Add real-time permission revocation broadcast (`ADDITIONS.md`). |
| EX5 | Snapshot flood attempts | `POST /collaboration/documents/{id}/snapshots...`, `POST /auto-snapshot` | Interval/state preconditions | Add per-document snapshot throttling (`ADDITIONS.md`). |
| EX6 | Zombie session after disconnect | `POST /collaboration/sessions/end` | Explicit end endpoint | Add heartbeat + stale session cleanup job (`ADDITIONS.md`). |
| EX7 | Activity spam | `POST /collaboration/activity` | Valid activity type guard | Add per-user and per-document rate limits (`ADDITIONS.md`). |

## Coverage and Gap Link

1. Endpoint coverage is mapped to `SEQUENCE.md`.
2. Use case intent is defined in `USE_CASE.md`.
3. Reliability and scale controls are in `ADDITIONS.md`.
