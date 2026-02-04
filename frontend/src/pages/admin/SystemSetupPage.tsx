import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Permission, RbacPolicy, UserRole } from '@/types'

type SettingRow = { key: string; value: string }

const ROLE_ORDER: UserRole[] = [
  'system_admin',
  'admin',
  'manager',
  'editor',
  'viewer',
  'customer',
]

const PERMISSION_GROUPS: { label: string; permissions: { value: Permission; label: string }[] }[] =
  [
    {
      label: 'Document Viewing',
      permissions: [
        { value: 'view_public_docs', label: 'View public docs' },
        { value: 'view_internal_docs', label: 'View internal docs' },
        { value: 'view_company_docs', label: 'View company docs' },
      ],
    },
    {
      label: 'Document Management',
      permissions: [
        { value: 'create_document', label: 'Create documents' },
        { value: 'edit_document', label: 'Edit documents' },
        { value: 'delete_document', label: 'Delete documents' },
        { value: 'publish_document', label: 'Publish documents' },
        { value: 'assign_companies', label: 'Assign companies' },
      ],
    },
    {
      label: 'Review Workflow',
      permissions: [
        { value: 'submit_review', label: 'Submit review' },
        { value: 'approve_review', label: 'Approve review' },
        { value: 'approve_peer_review', label: 'Approve peer review' },
      ],
    },
    {
      label: 'Collaboration',
      permissions: [
        { value: 'add_comments', label: 'Add comments' },
        { value: 'submit_feedback', label: 'Submit feedback' },
        { value: 'download_attachments', label: 'Download attachments' },
      ],
    },
    {
      label: 'User Management',
      permissions: [
        { value: 'manage_users', label: 'Manage users' },
        { value: 'manage_editors', label: 'Manage editors' },
        { value: 'manage_companies', label: 'Manage companies' },
        { value: 'system_settings', label: 'System settings' },
        { value: 'manage_admins', label: 'Manage admins' },
      ],
    },
  ]

export default function SystemSetupPage() {
  const [settingsRows, setSettingsRows] = useState<SettingRow[]>([])
  const [rbacPolicies, setRbacPolicies] = useState<Record<UserRole, Set<Permission>>>({
    system_admin: new Set(),
    admin: new Set(),
    manager: new Set(),
    editor: new Set(),
    viewer: new Set(),
    customer: new Set(),
  })

  const settingsQuery = useQuery({
    queryKey: ['system-settings'],
    queryFn: () => api.getSystemSettings(),
  })

  const policiesQuery = useQuery({
    queryKey: ['rbac-policies'],
    queryFn: () => api.getRbacPolicies(),
  })

  useEffect(() => {
    if (!settingsQuery.data) return
    const entries = Object.entries(settingsQuery.data.settings || {})
    setSettingsRows(
      entries.map(([key, value]) => ({
        key,
        value: typeof value === 'string' ? value : JSON.stringify(value, null, 2),
      }))
    )
  }, [settingsQuery.data])

  useEffect(() => {
    if (!policiesQuery.data) return
    const next: Record<UserRole, Set<Permission>> = {
      system_admin: new Set(),
      admin: new Set(),
      manager: new Set(),
      editor: new Set(),
      viewer: new Set(),
      customer: new Set(),
    }
    policiesQuery.data.policies.forEach((policy) => {
      next[policy.role] = new Set(policy.permissions)
    })
    setRbacPolicies(next)
  }, [policiesQuery.data])

  const saveSettingsMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      api.updateSystemSettings({ settings: payload }),
    onSuccess: (data) => {
      const entries = Object.entries(data.settings || {})
      setSettingsRows(
        entries.map(([key, value]) => ({
          key,
          value: typeof value === 'string' ? value : JSON.stringify(value, null, 2),
        }))
      )
    },
  })

  const savePoliciesMutation = useMutation({
    mutationFn: (policies: RbacPolicy[]) => api.updateRbacPolicies({ policies }),
    onSuccess: (data) => {
      const next: Record<UserRole, Set<Permission>> = {
        system_admin: new Set(),
        admin: new Set(),
        manager: new Set(),
        editor: new Set(),
        viewer: new Set(),
        customer: new Set(),
      }
      data.policies.forEach((policy) => {
        next[policy.role] = new Set(policy.permissions)
      })
      setRbacPolicies(next)
    },
  })

  const handleAddSetting = () => {
    setSettingsRows((prev) => [...prev, { key: '', value: '' }])
  }

  const handleRemoveSetting = (index: number) => {
    setSettingsRows((prev) => prev.filter((_, i) => i !== index))
  }

  const handleSettingChange = (index: number, field: 'key' | 'value', value: string) => {
    setSettingsRows((prev) =>
      prev.map((row, i) => (i === index ? { ...row, [field]: value } : row))
    )
  }

  const parseSettingValue = (value: string) => {
    if (value.trim() === '') return ''
    try {
      return JSON.parse(value)
    } catch {
      return value
    }
  }

  const settingsPayload = useMemo(() => {
    const payload: Record<string, unknown> = {}
    settingsRows.forEach((row) => {
      const key = row.key.trim()
      if (!key) return
      payload[key] = parseSettingValue(row.value)
    })
    return payload
  }, [settingsRows])

  const policiesPayload = useMemo(() => {
    return ROLE_ORDER.map((role) => ({
      role,
      permissions: Array.from(rbacPolicies[role] || []).sort(),
    }))
  }, [rbacPolicies])

  const togglePermission = (role: UserRole, permission: Permission) => {
    setRbacPolicies((prev) => {
      const next = { ...prev }
      const set = new Set(next[role] || [])
      if (set.has(permission)) {
        set.delete(permission)
      } else {
        set.add(permission)
      }
      next[role] = set
      return next
    })
  }

  const isLoading = settingsQuery.isLoading || policiesQuery.isLoading
  const hasError = settingsQuery.isError || policiesQuery.isError

  if (hasError) {
    return (
      <div className="surface-card rounded-2xl p-6 text-rose-700 bg-rose-50">
        Failed to load system setup data. Please refresh.
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-display font-bold text-slate-900">System Setup</h1>
        <p className="text-slate-500 mt-1">Configure global settings and RBAC policies</p>
      </div>

      <div className="surface-card rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">System Settings</h2>
            <p className="text-slate-500 text-sm">
              Key/value settings stored in the CMS configuration store.
            </p>
          </div>
          <button onClick={handleAddSetting} className="btn-secondary">
            Add Setting
          </button>
        </div>

        {isLoading ? (
          <div className="text-slate-500">Loading settings...</div>
        ) : settingsRows.length === 0 ? (
          <div className="text-slate-500">No settings configured yet.</div>
        ) : (
          <div className="space-y-3">
            {settingsRows.map((row, index) => (
              <div key={`${row.key}-${index}`} className="grid grid-cols-12 gap-3 items-start">
                <input
                  className="input-field col-span-4"
                  placeholder="setting.key"
                  value={row.key}
                  onChange={(e) => handleSettingChange(index, 'key', e.target.value)}
                />
                <textarea
                  className="input-field col-span-7 min-h-[44px]"
                  placeholder='Value (JSON or text)'
                  value={row.value}
                  onChange={(e) => handleSettingChange(index, 'value', e.target.value)}
                />
                <button
                  className="col-span-1 text-slate-500 hover:text-rose-600"
                  onClick={() => handleRemoveSetting(index)}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-center justify-end">
          <button
            className="btn-primary"
            onClick={() => saveSettingsMutation.mutate(settingsPayload)}
            disabled={saveSettingsMutation.isPending}
          >
            {saveSettingsMutation.isPending ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>

      <div className="surface-card rounded-2xl p-6 space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">RBAC Policies</h2>
          <p className="text-slate-500 text-sm">
            Define role-based permissions and publish them to the ACL engine.
          </p>
        </div>

        {isLoading ? (
          <div className="text-slate-500">Loading policies...</div>
        ) : (
          <div className="space-y-6">
            {ROLE_ORDER.map((role) => (
              <div key={role} className="rounded-xl border border-slate-200 p-4">
                <h3 className="font-semibold text-slate-900 capitalize">{role.replace('_', ' ')}</h3>
                <div className="grid gap-4 mt-4 lg:grid-cols-2">
                  {PERMISSION_GROUPS.map((group) => (
                    <div key={group.label} className="space-y-2">
                      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        {group.label}
                      </div>
                      <div className="space-y-2">
                        {group.permissions.map((permission) => (
                          <label
                            key={permission.value}
                            className="flex items-center gap-2 text-sm text-slate-700"
                          >
                            <input
                              type="checkbox"
                              className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                              checked={rbacPolicies[role]?.has(permission.value) || false}
                              onChange={() => togglePermission(role, permission.value)}
                            />
                            {permission.label}
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-center justify-end">
          <button
            className="btn-primary"
            onClick={() => savePoliciesMutation.mutate(policiesPayload)}
            disabled={savePoliciesMutation.isPending}
          >
            {savePoliciesMutation.isPending ? 'Publishing...' : 'Save & Publish Policies'}
          </button>
        </div>
      </div>
    </div>
  )
}
