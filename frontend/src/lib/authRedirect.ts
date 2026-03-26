type LocationLike = {
  pathname?: string
  search?: string
  hash?: string
}

const AUTH_ROUTE_PREFIXES = ['/login', '/reset-password', '/accept-invitation']

function composePath(location: LocationLike | null | undefined): string {
  if (!location?.pathname) {
    return ''
  }
  return `${location.pathname}${location.search || ''}${location.hash || ''}`
}

export function buildLoginRedirect(location: LocationLike): string {
  const next = composePath(location)
  return next ? `/login?next=${encodeURIComponent(next)}` : '/login'
}

export function sanitizeReturnPath(candidate: string | null | undefined): string | null {
  if (!candidate) {
    return null
  }
  if (!candidate.startsWith('/') || candidate.startsWith('//')) {
    return null
  }
  if (AUTH_ROUTE_PREFIXES.some((prefix) => candidate === prefix || candidate.startsWith(`${prefix}?`))) {
    return null
  }
  return candidate
}

export function resolvePostLoginRedirect(params: {
  queryNext?: string | null
  stateFrom?: LocationLike | null
  fallbackPath: string
}): string {
  const nextFromQuery = sanitizeReturnPath(params.queryNext)
  if (nextFromQuery) {
    return nextFromQuery
  }

  const nextFromState = sanitizeReturnPath(composePath(params.stateFrom))
  if (nextFromState) {
    return nextFromState
  }

  return params.fallbackPath
}
