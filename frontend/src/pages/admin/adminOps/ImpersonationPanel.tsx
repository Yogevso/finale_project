import { useEffect, useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { api } from '@/lib/api'
import { ErrorState } from '@/components/ErrorState'
import { CardSkeleton } from '@/components/skeletons'
import type { ImpersonationSession } from '@/lib/api/adminOpsApi'
import { toast } from 'sonner'
import type { Tenant } from './types'

export default function ImpersonationPanel() {
  const [current, setCurrent] = useState<ImpersonationSession | null>(null)
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [loading, setLoading] = useState(true)
  const [hasError, setHasError] = useState(false)

  useEffect(() => {
    setHasError(false)
    Promise.all([
      api.getCurrentImpersonation(),
      api.getCompanies({ per_page: 100 }),
    ])
      .then(([impersonation, companies]) => {
        setCurrent(impersonation)
        setTenants(companies.items.map((company) => ({
          id: company.id,
          name: company.name,
          slug: company.slug,
          is_active: company.is_active,
        })))
      })
      .catch(() => {
        setHasError(true)
      })
      .finally(() => setLoading(false))
  }, [])

  const handleStart = async (tenantId: number) => {
    try {
      const session = await api.startImpersonation(tenantId)
      setCurrent(session)
      toast.success(`Now viewing as: ${session.target_tenant_name}`)
    } catch {
      toast.error('Failed to start impersonation')
    }
  }

  const handleEnd = async () => {
    try {
      await api.endImpersonation()
      setCurrent(null)
      toast.success('Impersonation ended')
    } catch {
      toast.error('Failed to end impersonation')
    }
  }

  if (loading) return <CardSkeleton count={3} />

  if (hasError) {
    return (
      <ErrorState
        title="Impersonation tools unavailable"
        message="We could not load the current impersonation session or tenant list."
      />
    )
  }

  return (
    <div className="space-y-4">
      {current?.is_active ? (
        <div className="flex items-center justify-between rounded-xl border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-center gap-3">
            <Eye className="text-amber-600" size={20} />
            <div>
              <p className="font-medium text-amber-800">
                Currently impersonating: {current.target_tenant_name}
              </p>
              <p className="text-xs text-amber-600">
                Started {new Date(current.started_at).toLocaleString()}
              </p>
            </div>
          </div>
          <button
            onClick={handleEnd}
            className="flex items-center gap-2 rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700"
          >
            <EyeOff size={16} />
            End Impersonation
          </button>
        </div>
      ) : null}

      <div className="rounded-xl border bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold">Select Tenant to Impersonate</h2>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {tenants.map((tenant) => (
            <button
              key={tenant.id}
              onClick={() => handleStart(tenant.id)}
              disabled={current?.is_active && current.target_tenant_id === tenant.id}
              className="flex items-center justify-between rounded-lg border p-3 text-left hover:bg-slate-50 disabled:opacity-50"
            >
              <div>
                <p className="font-medium">{tenant.name}</p>
                <p className="text-xs text-slate-500">{tenant.slug}</p>
              </div>
              <span
                className={`rounded-full px-2 py-0.5 text-xs ${
                  tenant.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                }`}
              >
                {tenant.is_active ? 'Active' : 'Suspended'}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
