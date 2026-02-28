# Feature Rollout Flags

This project uses config-driven feature flags for architecture rollouts and rollback safety.

## Backend Flags

- `FEATURE_FLAG_PROJECTION_CACHE`
  - `true` (default): heavy analytics/search/portal reads use projection cache path.
  - `false`: bypass projection cache and execute direct query-handler reads.
- `FEATURE_FLAG_IDEMPOTENCY_MIDDLEWARE`
  - `true` (default): idempotency middleware is enabled for selected write endpoints.
  - `false`: middleware is not mounted and requests are processed without idempotency replay logic.
- `FEATURE_FLAG_EVENT_SOURCING_REVIEW_PILOT`
  - `false` (default): review workflow event-sourcing pilot is disabled.
  - `true`: shadow event streams are appended for review workflow pilot operations.

## Frontend Flags

- `VITE_FF_OPTIMISTIC_CONCURRENCY_HEADERS`
  - `true` (default): frontend sends `If-Match` headers for document/version update calls when available.
  - `false`: frontend skips `If-Match` headers (backend still supports optimistic concurrency when headers are sent by other clients).

## Rollout Procedure

1. Deploy with all flags enabled in staging (`true`).
2. Validate smoke checks for write/retry, search/portal/analytics reads, and edit/save flows.
3. Enable in production at low-risk window (single region or low-traffic period first).
4. Monitor:
   - API error rates for document/version update and publish/comment/review flows.
   - Read latency for analytics/search/portal endpoints.
5. If regression appears, rollback by setting the relevant flag(s) to `false` and restarting services.

## Rollback Procedure

1. Set the failing pathway flag to `false` in environment config.
2. Restart backend/frontend deployments.
3. Re-run targeted smoke checks for affected endpoints/pages.
4. Keep flag disabled while root-cause fix is prepared.

## Test Coverage

- Backend flag behavior and middleware toggling: `backend/tests/test_feature_flags.py`
- Projection/cache fallback behavior with cache framework: `backend/tests/test_projection_cache.py`
