import { useCallback, useEffect, useState } from 'react'
import { Activity, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'
import { api } from '@/lib/api'
import { ErrorState } from '@/components/ErrorState'
import { CardSkeleton } from '@/components/skeletons'
import type { SystemStatus } from '@/lib/api/adminOpsApi'

export default function SystemStatusPanel() {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [hasError, setHasError] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(() => {
    setHasError(false)
    setRefreshing(true)
    api.getSystemStatus()
      .then(setStatus)
      .catch(() => setHasError(true))
      .finally(() => {
        setLoading(false)
        setRefreshing(false)
      })
  }, [])

  useEffect(() => {
    load()
  }, [load])

  if (loading) return <CardSkeleton count={4} />

  if (hasError || !status) {
    return (
      <ErrorState
        title="System status unavailable"
        message="We could not load the live service health summary."
        onRetry={load}
      />
    )
  }

  const statusColor = (value: string) =>
    value === 'healthy' ? 'text-green-600' : value === 'degraded' ? 'text-yellow-600' : 'text-red-600'
  const statusBg = (value: string) =>
    value === 'healthy'
      ? 'bg-green-50 border-green-200'
      : value === 'degraded'
        ? 'bg-yellow-50 border-yellow-200'
        : 'bg-red-50 border-red-200'
  const StatusIcon = ({ statusValue }: { statusValue: string }) =>
    statusValue === 'healthy' ? (
      <CheckCircle className="text-green-500" size={20} />
    ) : statusValue === 'degraded' ? (
      <AlertTriangle className="text-yellow-500" size={20} />
    ) : (
      <XCircle className="text-red-500" size={20} />
    )

  return (
    <div className="space-y-4">
      <div className="rounded-xl border bg-white p-6">
        <div className="mb-4 flex items-center gap-3">
          <Activity className="text-slate-400" size={20} />
          <h2 className="text-lg font-semibold">Overall Status</h2>
          <span className={`ml-auto text-sm font-bold uppercase ${statusColor(status.overall || 'unknown')}`}>
            {status.overall || 'Unknown'}
          </span>
        </div>

        {status.checked_at ? (
          <p className="mb-4 text-xs text-slate-400">
            Last checked: {new Date(status.checked_at).toLocaleString()}
            <button
              onClick={load}
              disabled={refreshing}
              className="ml-2 text-indigo-500 underline hover:text-indigo-700 disabled:opacity-50"
            >
              {refreshing ? 'Refreshing...' : 'Refresh'}
            </button>
          </p>
        ) : null}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          {status.services.map((service) => (
            <div key={service.name}>
              <button
                onClick={() => setExpanded(expanded === service.name ? null : service.name)}
                className={`w-full rounded-lg border p-4 text-left transition-all ${
                  expanded === service.name
                    ? statusBg(service.status)
                    : 'border-slate-100 bg-slate-50 hover:border-slate-300'
                }`}
              >
                <div className="flex items-center gap-3">
                  <StatusIcon statusValue={service.status} />
                  <div className="min-w-0 flex-1">
                    <p className="font-medium capitalize">{service.name}</p>
                    <p className="truncate text-xs text-slate-500">{service.status}</p>
                  </div>
                  <svg
                    className={`h-4 w-4 text-slate-400 transition-transform ${expanded === service.name ? 'rotate-180' : ''}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </button>

              {expanded === service.name ? (
                <div className={`mt-1 space-y-2 rounded-lg border p-4 text-sm ${statusBg(service.status)}`}>
                  <div className="flex justify-between">
                    <span className="text-slate-600">Status</span>
                    <span className={`font-semibold uppercase ${statusColor(service.status)}`}>{service.status}</span>
                  </div>
                  {service.latency_ms !== null && service.latency_ms !== undefined ? (
                    <div className="flex justify-between">
                      <span className="text-slate-600">Latency</span>
                      <span
                        className={`font-medium ${
                          service.latency_ms < 100
                            ? 'text-green-600'
                            : service.latency_ms < 500
                              ? 'text-yellow-600'
                              : 'text-red-600'
                        }`}
                      >
                        {service.latency_ms}ms
                      </span>
                    </div>
                  ) : null}
                  {service.details ? (
                    <div className="border-t border-slate-200 pt-2">
                      <p className="mb-1 text-xs font-medium text-slate-600">Details</p>
                      <p className="text-slate-700">{service.details}</p>
                    </div>
                  ) : null}
                  {service.status !== 'healthy' ? (
                    <div className="border-t border-slate-200 pt-2">
                      <p className="mb-1 text-xs font-medium text-red-600">Action Required</p>
                      <p className="text-xs text-slate-700">
                        {service.status === 'down'
                          ? `The ${service.name} service is down. Check server logs and connectivity.`
                          : `The ${service.name} service is degraded. Performance may be affected.`}
                      </p>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
