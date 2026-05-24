export type FrontendFeatureFlag = 'optimisticConcurrencyHeaders' | 'documentViewRevamp'

type FrontendFeatureFlagState = Record<FrontendFeatureFlag, boolean>

export function parseBooleanFlag(rawValue: unknown, defaultValue: boolean): boolean {
  if (typeof rawValue === 'boolean') {
    return rawValue
  }
  if (typeof rawValue !== 'string') {
    return defaultValue
  }

  const normalized = rawValue.trim().toLowerCase()
  if (['1', 'true', 'yes', 'on'].includes(normalized)) {
    return true
  }
  if (['0', 'false', 'no', 'off'].includes(normalized)) {
    return false
  }
  return defaultValue
}

export function resolveFrontendFeatureFlags(
  env: Record<string, unknown>,
): FrontendFeatureFlagState {
  return Object.freeze({
    optimisticConcurrencyHeaders: parseBooleanFlag(
      env.VITE_FF_OPTIMISTIC_CONCURRENCY_HEADERS,
      true,
    ),
    documentViewRevamp: parseBooleanFlag(env.VITE_FF_DOCUMENT_VIEW_REVAMP, true),
  })
}

export const frontendFeatureFlags: FrontendFeatureFlagState = resolveFrontendFeatureFlags(
  import.meta.env,
)

export function isFrontendFeatureEnabled(flag: FrontendFeatureFlag): boolean {
  return frontendFeatureFlags[flag]
}
