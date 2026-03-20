import { useCallback, useEffect, useState } from 'react'
import { ToggleLeft, ToggleRight } from 'lucide-react'
import { api } from '@/lib/api'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { TableSkeleton } from '@/components/skeletons'
import type { FeatureMatrix } from '@/lib/api/adminOpsApi'
import { toast } from 'sonner'

export default function FeatureMatrixPanel() {
  const [matrix, setMatrix] = useState<FeatureMatrix | null>(null)
  const [loading, setLoading] = useState(true)
  const [hasError, setHasError] = useState(false)

  const load = useCallback(() => {
    setHasError(false)
    setLoading(true)
    api.getFeatureMatrix()
      .then(setMatrix)
      .catch(() => setHasError(true))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const allKeys = Array.from(new Set(matrix?.tenants.flatMap((tenant) => Object.keys(tenant.features)) ?? [])).sort()

  const toggleFlag = async (tenantId: number, key: string, current: boolean) => {
    try {
      await api.updateTenantFeatures(tenantId, [{ feature_key: key, enabled: !current }])
      setMatrix((previous) => {
        if (!previous) return previous
        return {
          tenants: previous.tenants.map((tenant) =>
            tenant.tenant_id === tenantId
              ? { ...tenant, features: { ...tenant.features, [key]: !current } }
              : tenant,
          ),
        }
      })
    } catch {
      toast.error('Failed to toggle feature')
    }
  }

  if (loading) return <TableSkeleton rows={6} columns={4} />

  if (hasError || !matrix) {
    return (
      <ErrorState
        title="Feature matrix unavailable"
        message="We could not load tenant feature flags."
        onRetry={load}
      />
    )
  }

  return (
    <div className="space-y-4">
      <div className="overflow-auto rounded-xl border bg-white">
        {allKeys.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={<ToggleLeft className="h-8 w-8" aria-hidden="true" />}
              title="No feature flags configured"
              description="Feature controls will appear here once tenant-specific flags are defined."
            />
          </div>
        ) : (
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b bg-slate-50">
                <th className="px-4 py-3 text-left font-medium">Tenant</th>
                {allKeys.map((key) => (
                  <th key={key} className="px-4 py-3 text-center font-medium">{key}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {matrix.tenants.map((tenant) => (
                <tr key={tenant.tenant_id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium">{tenant.tenant_name}</td>
                  {allKeys.map((key) => {
                    const enabled = tenant.features[key] ?? false
                    return (
                      <td key={key} className="px-4 py-3 text-center">
                        <button onClick={() => void toggleFlag(tenant.tenant_id, key, enabled)} className="mx-auto">
                          {enabled ? (
                            <ToggleRight className="text-green-600" size={20} />
                          ) : (
                            <ToggleLeft className="text-slate-300" size={20} />
                          )}
                        </button>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
