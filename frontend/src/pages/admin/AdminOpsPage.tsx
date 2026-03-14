/**
 * Admin Operations Page (Wave Z)
 *
 * System-admin only dashboard for tenant management, impersonation,
 * action queue, feature flags, maintenance windows, etc.
 */

import { useEffect, useState } from 'react'
import { useAuth } from '@/lib/auth'
import { api } from '@/lib/api'
import type {
  AdminAction,
  ImpersonationSession,
  SystemStatus,
  TenantQuota,
  MaintenanceWindow,
  FeatureMatrix,
} from '@/lib/api/adminOpsApi'
import {
  Shield,
  Settings,
  Activity,
  Clock,
  Server,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Eye,
  EyeOff,
  Plus,
  Play,
  Square,
  Download,
  ToggleLeft,
  ToggleRight,
} from 'lucide-react'
import { toast } from 'sonner'

type Tab = 'overview' | 'impersonation' | 'actions' | 'tenants' | 'features' | 'maintenance'

interface Tenant {
  id: number
  name: string
  slug: string
  is_active: boolean
}

export default function AdminOpsPage() {
  const { user } = useAuth()
  const [tab, setTab] = useState<Tab>('overview')

  if (user?.role !== 'system_admin') {
    return <div className="p-8 text-red-600">Access denied. System admin only.</div>
  }

  const tabs: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: 'overview', label: 'System Status', icon: <Server size={16} /> },
    { key: 'impersonation', label: 'Impersonation', icon: <Eye size={16} /> },
    { key: 'actions', label: 'Action Queue', icon: <CheckCircle size={16} /> },
    { key: 'tenants', label: 'Tenant Management', icon: <Settings size={16} /> },
    { key: 'features', label: 'Feature Matrix', icon: <ToggleLeft size={16} /> },
    { key: 'maintenance', label: 'Maintenance', icon: <Clock size={16} /> },
  ]

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Shield className="h-7 w-7 text-indigo-600" />
        <h1 className="text-2xl font-bold text-slate-900">Admin Operations</h1>
        <span className="text-xs px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded-full font-medium ml-2">
          System Admin
        </span>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 border-b border-slate-200">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'}`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && <SystemStatusPanel />}
      {tab === 'impersonation' && <ImpersonationPanel />}
      {tab === 'actions' && <ActionQueuePanel />}
      {tab === 'tenants' && <TenantManagementPanel />}
      {tab === 'features' && <FeatureMatrixPanel />}
      {tab === 'maintenance' && <MaintenancePanel />}
    </div>
  )
}

// ── System Status (Z-006) ────────────────────────────────────────

function SystemStatusPanel() {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getSystemStatus().then(setStatus).finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSpinner />

  const statusColor = (s: string) =>
    s === 'healthy' ? 'text-green-600' : s === 'degraded' ? 'text-yellow-600' : 'text-red-600'
  const StatusIcon = ({ s }: { s: string }) =>
    s === 'healthy' ? <CheckCircle className="text-green-500" size={20} /> :
    s === 'degraded' ? <AlertTriangle className="text-yellow-500" size={20} /> :
    <XCircle className="text-red-500" size={20} />

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl border p-6">
        <div className="flex items-center gap-3 mb-4">
          <Activity className="text-slate-400" size={20} />
          <h2 className="text-lg font-semibold">Overall Status</h2>
          <span className={`text-sm font-bold uppercase ml-auto ${statusColor(status?.overall || 'unknown')}`}>
            {status?.overall || 'Unknown'}
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {status?.services.map(svc => (
            <div key={svc.name} className="flex items-center gap-3 p-4 bg-slate-50 rounded-lg">
              <StatusIcon s={svc.status} />
              <div>
                <p className="font-medium capitalize">{svc.name}</p>
                <p className="text-xs text-slate-500">{svc.details || svc.status}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Impersonation (Z-001) ────────────────────────────────────────

function ImpersonationPanel() {
  const [current, setCurrent] = useState<ImpersonationSession | null>(null)
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.getCurrentImpersonation(),
      api.getCompanies({ per_page: 100 }),
    ]).then(([imp, companies]) => {
      setCurrent(imp)
      setTenants(companies.items.map(c => ({ id: c.id, name: c.name, slug: c.slug, is_active: c.is_active })))
    }).finally(() => setLoading(false))
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

  if (loading) return <LoadingSpinner />

  return (
    <div className="space-y-4">
      {current?.is_active && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center justify-between">
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
            className="flex items-center gap-2 px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 text-sm font-medium"
          >
            <EyeOff size={16} />
            End Impersonation
          </button>
        </div>
      )}

      <div className="bg-white rounded-xl border p-6">
        <h2 className="text-lg font-semibold mb-4">Select Tenant to Impersonate</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {tenants.map(t => (
            <button
              key={t.id}
              onClick={() => handleStart(t.id)}
              disabled={current?.is_active && current.target_tenant_id === t.id}
              className="flex items-center justify-between p-3 border rounded-lg hover:bg-slate-50 disabled:opacity-50 text-left"
            >
              <div>
                <p className="font-medium">{t.name}</p>
                <p className="text-xs text-slate-500">{t.slug}</p>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full ${t.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                {t.is_active ? 'Active' : 'Suspended'}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Action Queue (Z-002) ─────────────────────────────────────────

function ActionQueuePanel() {
  const { user } = useAuth()
  const [actions, setActions] = useState<AdminAction[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('')

  const load = () => {
    setLoading(true)
    api.listAdminActions(filter || undefined).then(setActions).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [filter])

  const handleReview = async (id: number, approved: boolean) => {
    const comment = approved ? undefined : prompt('Reason for rejection:') || undefined
    try {
      await api.reviewAdminAction(id, approved, comment)
      toast.success(approved ? 'Action approved' : 'Action rejected')
      load()
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Review failed')
    }
  }

  const statusBadge = (s: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-700',
      approved: 'bg-green-100 text-green-700',
      rejected: 'bg-red-100 text-red-700',
      executed: 'bg-blue-100 text-blue-700',
    }
    return colors[s] || 'bg-slate-100 text-slate-700'
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <select
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>

      <div className="bg-white rounded-xl border divide-y">
        {loading ? (
          <div className="p-8 text-center"><LoadingSpinner /></div>
        ) : actions.length === 0 ? (
          <div className="p-8 text-center text-slate-500">No admin actions in queue</div>
        ) : actions.map(a => (
          <div key={a.id} className="p-4 flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium">{a.action_type.replace(/_/g, ' ')}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${statusBadge(a.status)}`}>{a.status}</span>
              </div>
              <p className="text-sm text-slate-500 mt-1">
                Requested by {a.requester_name || `#${a.requested_by}`}
                {a.target_tenant_name && ` • Target: ${a.target_tenant_name}`}
              </p>
              {a.reason && <p className="text-sm text-slate-600 mt-1 italic">"{a.reason}"</p>}
              <p className="text-xs text-slate-400 mt-1">{new Date(a.created_at).toLocaleString()}</p>
            </div>
            {a.status === 'pending' && a.requested_by !== user?.id && (
              <div className="flex gap-2">
                <button
                  onClick={() => handleReview(a.id, true)}
                  className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700"
                >
                  Approve
                </button>
                <button
                  onClick={() => handleReview(a.id, false)}
                  className="px-3 py-1.5 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700"
                >
                  Reject
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Tenant Management (Z-004, Z-008, Z-009, Z-011, Z-012) ───────

function TenantManagementPanel() {
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [quota, setQuota] = useState<TenantQuota | null>(null)
  const [loading, setLoading] = useState(true)
  const [showProvision, setShowProvision] = useState(false)

  // Provisioning form
  const [provForm, setProvForm] = useState({
    tenant_name: '', tenant_slug: '', admin_username: '', admin_email: '', admin_password: '', company_type: 'customer', contact_email: ''
  })

  useEffect(() => {
    api.getCompanies({ per_page: 100 }).then(r => {
      setTenants(r.items.map(c => ({ id: c.id, name: c.name, slug: c.slug, is_active: c.is_active })))
    }).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (selected) {
      api.getTenantQuota(selected).then(setQuota).catch(() => setQuota(null))
    }
  }, [selected])

  const handleSuspend = async (id: number) => {
    const reason = prompt('Suspension reason:')
    if (reason === null) return
    try {
      await api.suspendTenant(id, reason || undefined)
      setTenants(ts => ts.map(t => t.id === id ? { ...t, is_active: false } : t))
      toast.success('Tenant suspended')
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Suspension failed')
    }
  }

  const handleReactivate = async (id: number) => {
    try {
      await api.reactivateTenant(id)
      setTenants(ts => ts.map(t => t.id === id ? { ...t, is_active: true } : t))
      toast.success('Tenant reactivated')
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Reactivation failed')
    }
  }

  const handleExport = async (id: number) => {
    try {
      const data = await api.exportTenantData(id)
      const blob = new Blob([JSON.stringify(data.export_data, null, 2)], { type: 'application/json' })
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `tenant-${id}-export.json`
      a.click()
      URL.revokeObjectURL(a.href)
      toast.success('Export downloaded')
    } catch {
      toast.error('Export failed')
    }
  }

  const handleProvision = async () => {
    try {
      const result = await api.provisionTenant(provForm)
      toast.success(`Tenant "${result.tenant_name}" created with admin "${result.admin_username}"`)
      setShowProvision(false)
      setProvForm({ tenant_name: '', tenant_slug: '', admin_username: '', admin_email: '', admin_password: '', company_type: 'customer', contact_email: '' })
      // Refresh
      api.getCompanies({ per_page: 100 }).then(r => {
        setTenants(r.items.map(c => ({ id: c.id, name: c.name, slug: c.slug, is_active: c.is_active })))
      })
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Provisioning failed')
    }
  }

  const handleQuotaSave = async () => {
    if (!selected || !quota) return
    try {
      const updated = await api.updateTenantQuota(selected, {
        max_users: quota.max_users ?? undefined,
        max_documents: quota.max_documents ?? undefined,
        max_storage_mb: quota.max_storage_mb ?? undefined,
      })
      setQuota(updated)
      toast.success('Quota updated')
    } catch {
      toast.error('Quota update failed')
    }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Tenants</h2>
        <button
          onClick={() => setShowProvision(!showProvision)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm"
        >
          <Plus size={16} />
          Provision Tenant
        </button>
      </div>

      {/* Provisioning Form */}
      {showProvision && (
        <div className="bg-white rounded-xl border p-6 space-y-4">
          <h3 className="font-semibold">New Tenant Provisioning</h3>
          <div className="grid grid-cols-2 gap-4">
            <input placeholder="Tenant Name" value={provForm.tenant_name} onChange={e => setProvForm(f => ({ ...f, tenant_name: e.target.value }))} className="border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Slug (lowercase, hyphens)" value={provForm.tenant_slug} onChange={e => setProvForm(f => ({ ...f, tenant_slug: e.target.value }))} className="border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Admin Username" value={provForm.admin_username} onChange={e => setProvForm(f => ({ ...f, admin_username: e.target.value }))} className="border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Admin Email" type="email" value={provForm.admin_email} onChange={e => setProvForm(f => ({ ...f, admin_email: e.target.value }))} className="border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Admin Password" type="password" value={provForm.admin_password} onChange={e => setProvForm(f => ({ ...f, admin_password: e.target.value }))} className="border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Contact Email" type="email" value={provForm.contact_email} onChange={e => setProvForm(f => ({ ...f, contact_email: e.target.value }))} className="border rounded-lg px-3 py-2 text-sm" />
          </div>
          <div className="flex gap-2">
            <button onClick={handleProvision} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700">Create</button>
            <button onClick={() => setShowProvision(false)} className="px-4 py-2 border rounded-lg text-sm">Cancel</button>
          </div>
        </div>
      )}

      {/* Tenant List */}
      <div className="bg-white rounded-xl border divide-y">
        {tenants.map(t => (
          <div
            key={t.id}
            className={`p-4 flex items-center justify-between cursor-pointer hover:bg-slate-50 ${selected === t.id ? 'bg-indigo-50' : ''}`}
            onClick={() => setSelected(selected === t.id ? null : t.id)}
          >
            <div>
              <p className="font-medium">{t.name}</p>
              <p className="text-xs text-slate-500">{t.slug} · ID: {t.id}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-xs px-2 py-0.5 rounded-full ${t.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                {t.is_active ? 'Active' : 'Suspended'}
              </span>
              {t.is_active ? (
                <button onClick={e => { e.stopPropagation(); handleSuspend(t.id) }} className="text-xs px-3 py-1 border rounded-lg text-red-600 hover:bg-red-50">Suspend</button>
              ) : (
                <button onClick={e => { e.stopPropagation(); handleReactivate(t.id) }} className="text-xs px-3 py-1 border rounded-lg text-green-600 hover:bg-green-50">Reactivate</button>
              )}
              <button onClick={e => { e.stopPropagation(); handleExport(t.id) }} className="text-xs px-3 py-1 border rounded-lg text-slate-600 hover:bg-slate-50" title="Export">
                <Download size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Quota Editor */}
      {selected && quota && (
        <div className="bg-white rounded-xl border p-6 space-y-4">
          <h3 className="font-semibold">Quota — Tenant #{selected}</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-xs text-slate-500">Max Users</label>
              <input
                type="number"
                value={quota.max_users ?? ''}
                onChange={e => setQuota(q => q ? { ...q, max_users: e.target.value ? Number(e.target.value) : null } : q)}
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1"
              />
              <p className="text-xs text-slate-400 mt-1">Current: {quota.current_users}</p>
            </div>
            <div>
              <label className="text-xs text-slate-500">Max Documents</label>
              <input
                type="number"
                value={quota.max_documents ?? ''}
                onChange={e => setQuota(q => q ? { ...q, max_documents: e.target.value ? Number(e.target.value) : null } : q)}
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1"
              />
              <p className="text-xs text-slate-400 mt-1">Current: {quota.current_documents}</p>
            </div>
            <div>
              <label className="text-xs text-slate-500">Max Storage (MB)</label>
              <input
                type="number"
                value={quota.max_storage_mb ?? ''}
                onChange={e => setQuota(q => q ? { ...q, max_storage_mb: e.target.value ? Number(e.target.value) : null } : q)}
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1"
              />
            </div>
          </div>
          <button onClick={handleQuotaSave} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700">Save Quota</button>
        </div>
      )}
    </div>
  )
}

// ── Feature Matrix (Z-005) ───────────────────────────────────────

function FeatureMatrixPanel() {
  const [matrix, setMatrix] = useState<FeatureMatrix | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getFeatureMatrix().then(setMatrix).finally(() => setLoading(false))
  }, [])

  const allKeys = Array.from(
    new Set(matrix?.tenants.flatMap(t => Object.keys(t.features)) ?? [])
  ).sort()

  const toggleFlag = async (tenantId: number, key: string, current: boolean) => {
    try {
      await api.updateTenantFeatures(tenantId, [{ feature_key: key, enabled: !current }])
      setMatrix(prev => {
        if (!prev) return prev
        return {
          tenants: prev.tenants.map(t =>
            t.tenant_id === tenantId
              ? { ...t, features: { ...t.features, [key]: !current } }
              : t
          ),
        }
      })
    } catch {
      toast.error('Failed to toggle feature')
    }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl border overflow-auto">
        {allKeys.length === 0 ? (
          <div className="p-8 text-center text-slate-500">
            No feature flags configured yet. Use the tenant detail view to add features.
          </div>
        ) : (
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b bg-slate-50">
                <th className="text-left px-4 py-3 font-medium">Tenant</th>
                {allKeys.map(k => (
                  <th key={k} className="px-4 py-3 font-medium text-center">{k}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {matrix?.tenants.map(t => (
                <tr key={t.tenant_id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium">{t.tenant_name}</td>
                  {allKeys.map(k => {
                    const enabled = t.features[k] ?? false
                    return (
                      <td key={k} className="px-4 py-3 text-center">
                        <button onClick={() => toggleFlag(t.tenant_id, k, enabled)} className="mx-auto">
                          {enabled
                            ? <ToggleRight className="text-green-600" size={20} />
                            : <ToggleLeft className="text-slate-300" size={20} />
                          }
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

// ── Maintenance Windows (Z-018) ──────────────────────────────────

function MaintenancePanel() {
  const [windows, setWindows] = useState<MaintenanceWindow[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({
    title: '', description: '', scheduled_start: '', scheduled_end: '', is_read_only: true,
  })

  const load = () => {
    setLoading(true)
    api.listMaintenanceWindows().then(setWindows).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleCreate = async () => {
    try {
      await api.createMaintenanceWindow({
        title: form.title,
        description: form.description || undefined,
        scheduled_start: new Date(form.scheduled_start).toISOString(),
        scheduled_end: new Date(form.scheduled_end).toISOString(),
        is_read_only: form.is_read_only,
      })
      toast.success('Maintenance window created')
      setShowCreate(false)
      setForm({ title: '', description: '', scheduled_start: '', scheduled_end: '', is_read_only: true })
      load()
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Creation failed')
    }
  }

  const handleToggle = async (w: MaintenanceWindow) => {
    try {
      if (w.is_active) {
        await api.deactivateMaintenanceWindow(w.id)
        toast.success('Maintenance deactivated')
      } else {
        await api.activateMaintenanceWindow(w.id)
        toast.success('Maintenance activated')
      }
      load()
    } catch {
      toast.error('Toggle failed')
    }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Maintenance Windows</h2>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm"
        >
          <Plus size={16} />
          Schedule Maintenance
        </button>
      </div>

      {showCreate && (
        <div className="bg-white rounded-xl border p-6 space-y-4">
          <h3 className="font-semibold">Schedule New Window</h3>
          <div className="grid grid-cols-2 gap-4">
            <input placeholder="Title" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} className="border rounded-lg px-3 py-2 text-sm col-span-2" />
            <input type="datetime-local" value={form.scheduled_start} onChange={e => setForm(f => ({ ...f, scheduled_start: e.target.value }))} className="border rounded-lg px-3 py-2 text-sm" />
            <input type="datetime-local" value={form.scheduled_end} onChange={e => setForm(f => ({ ...f, scheduled_end: e.target.value }))} className="border rounded-lg px-3 py-2 text-sm" />
            <textarea placeholder="Description" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} className="border rounded-lg px-3 py-2 text-sm col-span-2" rows={2} />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.is_read_only} onChange={e => setForm(f => ({ ...f, is_read_only: e.target.checked }))} />
            Read-only mode during maintenance
          </label>
          <div className="flex gap-2">
            <button onClick={handleCreate} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700">Create</button>
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 border rounded-lg text-sm">Cancel</button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border divide-y">
        {windows.length === 0 ? (
          <div className="p-8 text-center text-slate-500">No maintenance windows scheduled</div>
        ) : windows.map(w => (
          <div key={w.id} className="p-4 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <p className="font-medium">{w.title}</p>
                {w.is_active && (
                  <span className="text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded-full animate-pulse">ACTIVE</span>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {new Date(w.scheduled_start).toLocaleString()} → {new Date(w.scheduled_end).toLocaleString()}
              </p>
              {w.description && <p className="text-sm text-slate-600 mt-1">{w.description}</p>}
            </div>
            <button
              onClick={() => handleToggle(w)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm ${
                w.is_active
                  ? 'bg-green-600 text-white hover:bg-green-700'
                  : 'bg-red-600 text-white hover:bg-red-700'
              }`}
            >
              {w.is_active ? <><Square size={14} /> Deactivate</> : <><Play size={14} /> Activate</>}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Shared Components ────────────────────────────────────────────

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-8">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
    </div>
  )
}
