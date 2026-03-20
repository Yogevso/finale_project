import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import PageHeader from '@/components/PageHeader'
import { FormField, SubmitButton } from '@/components/form'
import { ErrorState } from '@/components/ErrorState'
import { FormSkeleton } from '@/components/skeletons'
import type {
  AudienceAlertRule,
  AudienceAlertRuleCreate,
  Permission,
  RbacPolicy,
  UserRole,
} from '@/types'

type SettingRow = { key: string; value: string }
type AlertRuleFormState = {
  metric: string
  threshold: string
  window_minutes: string
  document_id: string
  enabled: boolean
}

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
  const [audienceAlertRules, setAudienceAlertRules] = useState<AudienceAlertRule[]>([])
  const [alertRuleForm, setAlertRuleForm] = useState<AlertRuleFormState>({
    metric: 'visibility_changes_per_document',
    threshold: '5',
    window_minutes: '60',
    document_id: '',
    enabled: true,
  })
  const [alertRuleErrors, setAlertRuleErrors] = useState<{
    metric?: string
    threshold?: string
    window_minutes?: string
    document_id?: string
  }>({})

  const settingsQuery = useQuery({
    queryKey: ['system-settings'],
    queryFn: () => api.getSystemSettings(),
  })

  const policiesQuery = useQuery({
    queryKey: ['rbac-policies'],
    queryFn: () => api.getRbacPolicies(),
  })

  const alertRulesQuery = useQuery({
    queryKey: ['audience-alert-rules'],
    queryFn: () => api.listAudienceAlertRules(),
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

  useEffect(() => {
    if (!alertRulesQuery.data) return
    setAudienceAlertRules(alertRulesQuery.data)
  }, [alertRulesQuery.data])

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

  const createAlertRuleMutation = useMutation({
    mutationFn: (payload: AudienceAlertRuleCreate) => api.createAudienceAlertRule(payload),
    onSuccess: (createdRule) => {
      setAudienceAlertRules((prev) => [...prev, createdRule])
      setAlertRuleForm((prev) => ({ ...prev, document_id: '' }))
      setAlertRuleErrors({})
    },
  })

  const deleteAlertRuleMutation = useMutation({
    mutationFn: (ruleId: string) => api.deleteAudienceAlertRule(ruleId),
    onSuccess: (_, ruleId) => {
      setAudienceAlertRules((prev) => prev.filter((rule) => rule.id !== ruleId))
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

  const handleCreateAlertRule = () => {
    const nextErrors: typeof alertRuleErrors = {}
    const threshold = Number(alertRuleForm.threshold)
    const windowMinutes = Number(alertRuleForm.window_minutes)

    if (!alertRuleForm.metric.trim()) {
      nextErrors.metric = 'Metric is required'
    }

    if (!Number.isInteger(threshold) || threshold < 1) {
      nextErrors.threshold = 'Threshold must be a whole number greater than 0'
    }

    if (!Number.isInteger(windowMinutes) || windowMinutes < 1) {
      nextErrors.window_minutes = 'Window must be a whole number greater than 0'
    }

    if (alertRuleForm.document_id.trim()) {
      const documentId = Number(alertRuleForm.document_id)
      if (!Number.isInteger(documentId) || documentId < 1) {
        nextErrors.document_id = 'Document ID must be a whole number greater than 0'
      }
    }

    if (Object.keys(nextErrors).length > 0) {
      setAlertRuleErrors(nextErrors)
      return
    }

    setAlertRuleErrors({})
    createAlertRuleMutation.mutate({
      metric: alertRuleForm.metric.trim(),
      threshold,
      window_minutes: windowMinutes,
      document_id: alertRuleForm.document_id.trim()
        ? Number(alertRuleForm.document_id)
        : undefined,
      enabled: alertRuleForm.enabled,
    })
  }

  const isLoading = settingsQuery.isLoading || policiesQuery.isLoading || alertRulesQuery.isLoading
  const hasError = settingsQuery.isError || policiesQuery.isError || alertRulesQuery.isError

  if (hasError) {
    return (
      <ErrorState
        title="System setup unavailable"
        message="We could not load the global settings, RBAC policies, or alert rules."
        onRetry={() => {
          void settingsQuery.refetch()
          void policiesQuery.refetch()
          void alertRulesQuery.refetch()
        }}
      />
    )
  }

  return (
    <div className="page-stack-lg">
      <PageHeader
        title="System Setup"
        subtitle="Configure global settings, RBAC policies, and audience governance alerts."
      />

      <div className="surface-card rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="section-title">System Settings</h2>
            <p className="body-copy">
              Key/value settings stored in the CMS configuration store.
            </p>
          </div>
          <button type="button" onClick={handleAddSetting} className="btn-secondary table-action-btn">
            Add Setting
          </button>
        </div>

        {isLoading ? (
          <FormSkeleton fields={4} />
        ) : settingsRows.length === 0 ? (
          <div className="body-copy">No settings configured yet.</div>
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
                  type="button"
                  className="btn-danger table-action-btn col-span-1"
                  onClick={() => handleRemoveSetting(index)}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-center justify-end">
          <SubmitButton
            onClick={() => saveSettingsMutation.mutate(settingsPayload)}
            isLoading={saveSettingsMutation.isPending}
            loadingText="Saving..."
          >
            Save Settings
          </SubmitButton>
        </div>
      </div>

      <div className="surface-card rounded-2xl p-6 space-y-4">
        <div>
          <h2 className="section-title">RBAC Policies</h2>
          <p className="body-copy">
            Define role-based permissions and publish them to the ACL engine.
          </p>
        </div>

        {isLoading ? (
          <FormSkeleton fields={6} />
        ) : (
          <div className="space-y-6">
            {ROLE_ORDER.map((role) => (
              <div key={role} className="rounded-xl border border-slate-200 p-4">
                <h3 className="card-title capitalize">{role.replace('_', ' ')}</h3>
                <div className="grid gap-4 mt-4 lg:grid-cols-2">
                  {PERMISSION_GROUPS.map((group) => (
                    <div key={group.label} className="space-y-2">
                      <div className="helper-copy font-semibold uppercase tracking-wide">
                        {group.label}
                      </div>
                      <div className="space-y-2">
                        {group.permissions.map((permission) => (
                          <label
                            key={permission.value}
                            className="body-copy flex items-center gap-2 text-slate-700 dark:text-slate-300"
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
          <SubmitButton
            onClick={() => savePoliciesMutation.mutate(policiesPayload)}
            isLoading={savePoliciesMutation.isPending}
            loadingText="Publishing..."
          >
            Save & Publish Policies
          </SubmitButton>
        </div>
      </div>

      <div className="surface-card rounded-2xl p-6 space-y-4" data-testid="audience-alert-rules-section">
        <div>
          <h2 className="section-title">Audience Alert Rules</h2>
          <p className="body-copy">
            Configure threshold-based audience governance alerts.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-6 gap-3 items-end">
          <FormField
            label="Metric"
            htmlFor="audience-alert-rule-metric"
            required
            error={alertRuleErrors.metric}
            className="md:col-span-2"
          >
            <input
              id="audience-alert-rule-metric"
              className="input-field"
              value={alertRuleForm.metric}
              onChange={(e) => {
                setAlertRuleForm((prev) => ({ ...prev, metric: e.target.value }))
                setAlertRuleErrors((prev) => ({ ...prev, metric: undefined }))
              }}
              placeholder="visibility_changes_per_document"
              data-testid="audience-alert-rule-metric"
              aria-invalid={!!alertRuleErrors.metric}
            />
          </FormField>
          <FormField
            label="Threshold"
            htmlFor="audience-alert-rule-threshold"
            required
            error={alertRuleErrors.threshold}
          >
            <input
              id="audience-alert-rule-threshold"
              className="input-field"
              type="number"
              min={1}
              value={alertRuleForm.threshold}
              onChange={(e) => {
                setAlertRuleForm((prev) => ({ ...prev, threshold: e.target.value }))
                setAlertRuleErrors((prev) => ({ ...prev, threshold: undefined }))
              }}
              data-testid="audience-alert-rule-threshold"
              aria-invalid={!!alertRuleErrors.threshold}
            />
          </FormField>
          <FormField
            label="Window (min)"
            htmlFor="audience-alert-rule-window"
            required
            error={alertRuleErrors.window_minutes}
          >
            <input
              id="audience-alert-rule-window"
              className="input-field"
              type="number"
              min={1}
              value={alertRuleForm.window_minutes}
              onChange={(e) => {
                setAlertRuleForm((prev) => ({ ...prev, window_minutes: e.target.value }))
                setAlertRuleErrors((prev) => ({ ...prev, window_minutes: undefined }))
              }}
              data-testid="audience-alert-rule-window"
              aria-invalid={!!alertRuleErrors.window_minutes}
            />
          </FormField>
          <FormField
            label="Document ID"
            htmlFor="audience-alert-rule-document"
            hint="Optional"
            error={alertRuleErrors.document_id}
          >
            <input
              id="audience-alert-rule-document"
              className="input-field"
              type="number"
              min={1}
              value={alertRuleForm.document_id}
              onChange={(e) => {
                setAlertRuleForm((prev) => ({ ...prev, document_id: e.target.value }))
                setAlertRuleErrors((prev) => ({ ...prev, document_id: undefined }))
              }}
              placeholder="Optional"
              data-testid="audience-alert-rule-document"
              aria-invalid={!!alertRuleErrors.document_id}
            />
          </FormField>
          <div className="flex items-center gap-2">
            <input
              id="audience-alert-rule-enabled"
              type="checkbox"
              checked={alertRuleForm.enabled}
              onChange={(e) => setAlertRuleForm((prev) => ({ ...prev, enabled: e.target.checked }))}
            />
            <label htmlFor="audience-alert-rule-enabled" className="body-copy text-slate-700 dark:text-slate-300">
              Enabled
            </label>
          </div>
        </div>

        <div className="flex items-center justify-end">
          <SubmitButton
            type="button"
            onClick={handleCreateAlertRule}
            isLoading={createAlertRuleMutation.isPending}
            loadingText="Creating..."
            data-testid="audience-alert-rule-create"
          >
            Create Rule
          </SubmitButton>
        </div>

        {audienceAlertRules.length === 0 ? (
          <div className="body-copy">No audience alert rules configured.</div>
        ) : (
          <ul className="space-y-2" data-testid="audience-alert-rule-list">
            {audienceAlertRules.map((rule) => (
              <li
                key={rule.id}
                className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-3 py-2"
                data-testid={`audience-alert-rule-${rule.id}`}
              >
                <div className="body-copy text-slate-700 dark:text-slate-300">
                  <span className="font-semibold">{rule.metric}</span>
                  <span className="mx-2 text-slate-400">|</span>
                  {rule.threshold} in {rule.window_minutes}m
                  {rule.document_id ? ` | doc ${rule.document_id}` : ' | all docs'}
                  {rule.enabled ? ' | enabled' : ' | disabled'}
                </div>
                <button
                  type="button"
                  className="btn-danger table-action-btn"
                  onClick={() => deleteAlertRuleMutation.mutate(rule.id)}
                  disabled={deleteAlertRuleMutation.isPending}
                  data-testid={`audience-alert-rule-delete-${rule.id}`}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
