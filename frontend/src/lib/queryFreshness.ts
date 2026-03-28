export const audienceSensitiveQueryOptions = {
  staleTime: 0,
  refetchOnMount: 'always' as const,
  refetchOnWindowFocus: true,
}

export function fetchFresh(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  return fetch(input, {
    ...(init ?? {}),
    cache: 'no-store',
  })
}
