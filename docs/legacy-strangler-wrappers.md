# Legacy Strangler Wrappers

Task 108 introduces explicit wrapper boundaries for legacy-heavy modules so replacement can happen incrementally.

## Wrapped Boundaries

- `analytics_service` wrapper
  - Legacy module: `app.services.analytics_service`
  - Wrapper: `app.legacy_wrappers.analytics.AnalyticsServiceStranglerWrapper`
- `document_converter` wrapper
  - Legacy module: `app.utils.document_converter`
  - Wrapper: `app.legacy_wrappers.document_converter.DocumentConverterStranglerWrapper`

## Tracking Call Volume and Migration Progress

Wrapper usage and completion metadata are tracked via:

- `app.legacy_wrappers.tracking.get_legacy_wrapper_tracker()`

Status snapshot fields:

- `wrapper_name`
- `legacy_module`
- `migration_completion_percent`
- `call_volume`

## Rollout Guidance

1. Keep routes/services calling wrappers only (no direct legacy imports in migration targets).
2. Replace internals under wrapper interface in small slices.
3. Monitor wrapper `call_volume` to confirm traffic path and detect regressions.
4. Increase `migration_completion_percent` as internals are replaced.
