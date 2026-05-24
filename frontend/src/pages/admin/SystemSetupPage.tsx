import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { extractApiErrorMessage, useToast } from '@/lib/toast'
import PageHeader from '@/components/PageHeader'
import { FormField, SubmitButton } from '@/components/form'
import { ErrorState } from '@/components/ErrorState'
import { FormSkeleton } from '@/components/skeletons'
import type {
  ArchiveRetentionUnit,
  AudienceAlertRule,
  AudienceAlertRuleCreate,
  EmailSecurityMode,
  Permission,
  RbacPolicy,
  SystemDocumentLifecycleSettings,
  SystemDocumentLifecycleSettingsUpdate,
  SystemEmailSettings,
  SystemEmailSettingsUpdate,
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
type EmailSettingsDraft = {
  enabled: boolean
  host: string
  port: string
  security: EmailSecurityMode
  username: string
  password: string
  clear_password: boolean
  from_email: string
  from_name: string
}
type EmailSettingsErrors = {
  host?: string
  port?: string
  from_email?: string
  from_name?: string
}
type DocumentLifecycleDraft = {
  auto_archive_enabled: boolean
  auto_archive_after_value: string
  auto_archive_after_unit: ArchiveRetentionUnit
}
type DocumentLifecycleErrors = {
  auto_archive_after_value?: string
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

const EMPTY_PERMISSION_MAP = (): Record<UserRole, Set<Permission>> => ({
  system_admin: new Set(),
  admin: new Set(),
  manager: new Set(),
  editor: new Set(),
  viewer: new Set(),
  customer: new Set(),
})

const EMPTY_EMAIL_DRAFT: EmailSettingsDraft = {
  enabled: true,
  host: '',
  port: '587',
  security: 'starttls',
  username: '',
  password: '',
  clear_password: false,
  from_email: '',
  from_name: '',
}
const EMPTY_DOCUMENT_LIFECYCLE_DRAFT: DocumentLifecycleDraft = {
  auto_archive_enabled: false,
  auto_archive_after_value: '12',
  auto_archive_after_unit: 'months',
}

function mapSettingsToRows(settings: Record<string, unknown>): SettingRow[] {
  return Object.entries(settings || {}).map(([key, value]) => ({
    key,
    value: typeof value === 'string' ? value : JSON.stringify(value, null, 2),
  }))
}

function mapPoliciesToState(policies: RbacPolicy[]): Record<UserRole, Set<Permission>> {
  const next = EMPTY_PERMISSION_MAP()
  policies.forEach((policy) => {
    next[policy.role] = new Set(policy.permissions)
  })
  return next
}

function buildEmailDraft(settings: SystemEmailSettings): EmailSettingsDraft {
  return {
    enabled: settings.enabled,
    host: settings.host ?? '',
    port: String(settings.port ?? 587),
    security: settings.security ?? 'starttls',
    username: settings.username ?? '',
    password: '',
    clear_password: false,
    from_email: settings.from_email ?? '',
    from_name: settings.from_name ?? '',
  }
}

function validateEmailDraft(draft: EmailSettingsDraft): EmailSettingsErrors {
  const nextErrors: EmailSettingsErrors = {}
  const port = Number(draft.port)

  if (draft.enabled && !draft.host.trim()) {
    nextErrors.host = 'SMTP host is required when email delivery is enabled'
  }

  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    nextErrors.port = 'Port must be a whole number between 1 and 65535'
  }

  if (!draft.from_email.trim()) {
    nextErrors.from_email = 'Sender email is required'
  }

  if (!draft.from_name.trim()) {
    nextErrors.from_name = 'Sender name is required'
  }

  return nextErrors
}

function buildDocumentLifecycleDraft(
  settings: SystemDocumentLifecycleSettings,
): DocumentLifecycleDraft {
  return {
    auto_archive_enabled: settings.auto_archive_enabled,
    auto_archive_after_value: String(settings.auto_archive_after_value ?? 12),
    auto_archive_after_unit: settings.auto_archive_after_unit ?? 'months',
  }
}

function validateDocumentLifecycleDraft(
  draft: DocumentLifecycleDraft,
): DocumentLifecycleErrors {
  const nextErrors: DocumentLifecycleErrors = {}
  const value = Number(draft.auto_archive_after_value)

  if (!Number.isInteger(value) || value < 1 || value > 1200) {
    nextErrors.auto_archive_after_value = 'Archive after must be a whole number between 1 and 1200'
  }

  return nextErrors
}

function toEmailSettingsPayload(draft: EmailSettingsDraft): SystemEmailSettingsUpdate {
  return {
    enabled: draft.enabled,
    host: draft.host.trim() || null,
    port: Number(draft.port),
    security: draft.security,
    username: draft.username.trim() || null,
    password: draft.clear_password ? null : draft.password || null,
    clear_password: draft.clear_password,
    from_email: draft.from_email.trim(),
    from_name: draft.from_name.trim(),
  }
}

function toDocumentLifecycleSettingsPayload(
  draft: DocumentLifecycleDraft,
): SystemDocumentLifecycleSettingsUpdate {
  return {
    auto_archive_enabled: draft.auto_archive_enabled,
    auto_archive_after_value: Number(draft.auto_archive_after_value),
    auto_archive_after_unit: draft.auto_archive_after_unit,
  }
}

function formatEmailSource(source: 'database' | 'environment'): string {
  return source === 'database' ? 'Database override' : 'Environment default'
}

function formatDocumentLifecycleSource(source: 'database' | 'default'): string {
  return source === 'database' ? 'Database override' : 'System default'
}

function formatTimestamp(value?: string | null): string | null {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

export default function SystemSetupPage() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [settingsRows, setSettingsRows] = useState<SettingRow[]>([])
  const [rbacPolicies, setRbacPolicies] = useState<Record<UserRole, Set<Permission>>>(
    EMPTY_PERMISSION_MAP,
  )
  const [audienceAlertRules, setAudienceAlertRules] = useState<AudienceAlertRule[]>([])
  const [emailSettingsDraft, setEmailSettingsDraft] = useState<EmailSettingsDraft>(
    EMPTY_EMAIL_DRAFT,
  )
  const [emailSettingsErrors, setEmailSettingsErrors] = useState<EmailSettingsErrors>({})
  const [emailSettingsDirty, setEmailSettingsDirty] = useState(false)
  const [documentLifecycleDraft, setDocumentLifecycleDraft] =
    useState<DocumentLifecycleDraft>(EMPTY_DOCUMENT_LIFECYCLE_DRAFT)
  const [documentLifecycleErrors, setDocumentLifecycleErrors] =
    useState<DocumentLifecycleErrors>({})
  const [documentLifecycleDirty, setDocumentLifecycleDirty] = useState(false)
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

  const documentLifecycleQuery = useQuery({
    queryKey: ['system-document-lifecycle-settings'],
    queryFn: () => api.getSystemDocumentLifecycleSettings(),
  })

  const emailSettingsQuery = useQuery({
    queryKey: ['system-email-settings'],
    queryFn: () => api.getSystemEmailSettings(),
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
    setSettingsRows(mapSettingsToRows(settingsQuery.data.settings || {}))
  }, [settingsQuery.data])

  useEffect(() => {
    if (!documentLifecycleQuery.data || documentLifecycleDirty) return
    setDocumentLifecycleDraft(buildDocumentLifecycleDraft(documentLifecycleQuery.data.settings))
    setDocumentLifecycleErrors({})
  }, [documentLifecycleDirty, documentLifecycleQuery.data])

  useEffect(() => {
    if (!emailSettingsQuery.data || emailSettingsDirty) return
    setEmailSettingsDraft(buildEmailDraft(emailSettingsQuery.data.settings))
    setEmailSettingsErrors({})
  }, [emailSettingsDirty, emailSettingsQuery.data])

  useEffect(() => {
    if (!policiesQuery.data) return
    setRbacPolicies(mapPoliciesToState(policiesQuery.data.policies))
  }, [policiesQuery.data])

  useEffect(() => {
    if (!alertRulesQuery.data) return
    setAudienceAlertRules(alertRulesQuery.data)
  }, [alertRulesQuery.data])

  const saveSettingsMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      api.updateSystemSettings({ settings: payload }),
    onSuccess: (data) => {
      setSettingsRows(mapSettingsToRows(data.settings || {}))
      toast.success('System settings saved')
    },
    onError: (error) => {
      toast.error('Failed to save system settings', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  const saveDocumentLifecycleMutation = useMutation({
    mutationFn: (payload: SystemDocumentLifecycleSettingsUpdate) =>
      api.updateSystemDocumentLifecycleSettings(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(['system-document-lifecycle-settings'], data)
      setDocumentLifecycleDraft(buildDocumentLifecycleDraft(data.settings))
      setDocumentLifecycleErrors({})
      setDocumentLifecycleDirty(false)
      toast.success(
        'Document lifecycle settings saved',
        `Auto-archive ${data.settings.auto_archive_enabled ? 'enabled' : 'disabled'}`,
      )
    },
    onError: (error) => {
      toast.error(
        'Failed to save document lifecycle settings',
        extractApiErrorMessage(error, 'Please try again.'),
      )
    },
  })

  const saveEmailSettingsMutation = useMutation({
    mutationFn: (payload: SystemEmailSettingsUpdate) => api.updateSystemEmailSettings(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(['system-email-settings'], data)
      setEmailSettingsDraft(buildEmailDraft(data.settings))
      setEmailSettingsErrors({})
      setEmailSettingsDirty(false)
      toast.success(
        'Email delivery settings saved',
        `${data.settings.from_name} <${data.settings.from_email}>`,
      )
    },
    onError: (error) => {
      toast.error(
        'Failed to save email delivery settings',
        extractApiErrorMessage(error, 'Please try again.'),
      )
    },
  })

  const savePoliciesMutation = useMutation({
    mutationFn: (policies: RbacPolicy[]) => api.updateRbacPolicies({ policies }),
    onSuccess: (data) => {
      setRbacPolicies(mapPoliciesToState(data.policies))
      toast.success('RBAC policies published')
    },
    onError: (error) => {
      toast.error('Failed to publish RBAC policies', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  const createAlertRuleMutation = useMutation({
    mutationFn: (payload: AudienceAlertRuleCreate) => api.createAudienceAlertRule(payload),
    onSuccess: (createdRule) => {
      setAudienceAlertRules((prev) => [...prev, createdRule])
      setAlertRuleForm((prev) => ({ ...prev, document_id: '' }))
      setAlertRuleErrors({})
      toast.success('Audience alert rule created')
    },
    onError: (error) => {
      toast.error(
        'Failed to create audience alert rule',
        extractApiErrorMessage(error, 'Please try again.'),
      )
    },
  })

  const deleteAlertRuleMutation = useMutation({
    mutationFn: (ruleId: string) => api.deleteAudienceAlertRule(ruleId),
    onSuccess: (_, ruleId) => {
      setAudienceAlertRules((prev) => prev.filter((rule) => rule.id !== ruleId))
      toast.success('Audience alert rule deleted')
    },
    onError: (error) => {
      toast.error(
        'Failed to delete audience alert rule',
        extractApiErrorMessage(error, 'Please try again.'),
      )
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

  const handleEmailFieldChange = <K extends keyof EmailSettingsDraft>(
    field: K,
    value: EmailSettingsDraft[K],
  ) => {
    setEmailSettingsDirty(true)
    setEmailSettingsDraft((prev) => {
      if (field === 'password') {
        return { ...prev, password: value as string, clear_password: false }
      }
      if (field === 'clear_password') {
        return {
          ...prev,
          clear_password: value as boolean,
          password: value ? '' : prev.password,
        }
      }
      return { ...prev, [field]: value }
    })
    if (field in emailSettingsErrors) {
      setEmailSettingsErrors((prev) => ({ ...prev, [field]: undefined }))
    }
  }

  const handleDocumentLifecycleFieldChange = <K extends keyof DocumentLifecycleDraft>(
    field: K,
    value: DocumentLifecycleDraft[K],
  ) => {
    setDocumentLifecycleDirty(true)
    setDocumentLifecycleDraft((prev) => ({ ...prev, [field]: value }))
    if (field === 'auto_archive_after_value' && documentLifecycleErrors.auto_archive_after_value) {
      setDocumentLifecycleErrors((prev) => ({ ...prev, auto_archive_after_value: undefined }))
    }
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

  const handleSaveEmailSettings = () => {
    const nextErrors = validateEmailDraft(emailSettingsDraft)
    if (Object.keys(nextErrors).length > 0) {
      setEmailSettingsErrors(nextErrors)
      return
    }

    setEmailSettingsErrors({})
    saveEmailSettingsMutation.mutate(toEmailSettingsPayload(emailSettingsDraft))
  }

  const handleSaveDocumentLifecycleSettings = () => {
    const nextErrors = validateDocumentLifecycleDraft(documentLifecycleDraft)
    if (Object.keys(nextErrors).length > 0) {
      setDocumentLifecycleErrors(nextErrors)
      return
    }

    setDocumentLifecycleErrors({})
    saveDocumentLifecycleMutation.mutate(
      toDocumentLifecycleSettingsPayload(documentLifecycleDraft),
    )
  }

  const isLoading =
    settingsQuery.isLoading ||
    documentLifecycleQuery.isLoading ||
    emailSettingsQuery.isLoading ||
    policiesQuery.isLoading ||
    alertRulesQuery.isLoading
  const hasError =
    settingsQuery.isError ||
    documentLifecycleQuery.isError ||
    emailSettingsQuery.isError ||
    policiesQuery.isError ||
    alertRulesQuery.isError
  const documentLifecycleMetadata = documentLifecycleQuery.data
  const documentLifecycleUpdatedAt = formatTimestamp(documentLifecycleMetadata?.updated_at)
  const emailSettingsMetadata = emailSettingsQuery.data
  const emailUpdatedAt = formatTimestamp(emailSettingsMetadata?.updated_at)

  if (hasError) {
    return (
      <ErrorState
        title="System setup unavailable"
        message="We could not load the global settings, document lifecycle policy, email delivery settings, RBAC policies, or alert rules."
        onRetry={() => {
          void settingsQuery.refetch()
          void documentLifecycleQuery.refetch()
          void emailSettingsQuery.refetch()
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
        subtitle="Configure global settings, invitation sender credentials, RBAC policies, and audience governance alerts."
      />

      <div
        className="surface-card rounded-2xl p-6 space-y-5"
        data-testid="system-document-lifecycle-section"
      >
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-2">
            <div>
              <h2 className="section-title">Document Lifecycle</h2>
              <p className="body-copy">
                Configure when active documents should move to archive automatically.
              </p>
            </div>
            {documentLifecycleMetadata ? (
              <div className="grid gap-2 text-sm text-slate-600 dark:text-slate-300 md:grid-cols-2">
                <div>
                  <span className="font-semibold text-slate-800 dark:text-slate-100">Policy source:</span>{' '}
                  {formatDocumentLifecycleSource(documentLifecycleMetadata.source)}
                </div>
                <div>
                  <span className="font-semibold text-slate-800 dark:text-slate-100">Archive basis:</span>{' '}
                  {documentLifecycleMetadata.settings.auto_archive_basis.replace('_', ' ')}
                </div>
                <div>
                  <span className="font-semibold text-slate-800 dark:text-slate-100">Delete recovery window:</span>{' '}
                  {documentLifecycleMetadata.settings.delete_grace_days} days
                </div>
                <div>
                  <span className="font-semibold text-slate-800 dark:text-slate-100">Last update:</span>{' '}
                  {documentLifecycleUpdatedAt || 'System default'}
                  {documentLifecycleMetadata.updated_by
                    ? ` by user #${documentLifecycleMetadata.updated_by}`
                    : ''}
                </div>
              </div>
            ) : null}
          </div>
          <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-100 lg:max-w-md">
            Auto-archive only applies to active documents that already have a published version. Drafts and never-published items stay out of this policy.
          </div>
        </div>

        {isLoading ? (
          <FormSkeleton fields={3} />
        ) : (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 p-4 space-y-4">
              <div className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                <div>
                  <div className="font-semibold text-slate-900 dark:text-slate-100">Automatic archive policy</div>
                  <div className="text-sm text-slate-600 dark:text-slate-300">
                    Move active documents to archive once their latest published version ages out.
                  </div>
                </div>
                <label className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-200">
                  <input
                    type="checkbox"
                    checked={documentLifecycleDraft.auto_archive_enabled}
                    onChange={(e) =>
                      handleDocumentLifecycleFieldChange(
                        'auto_archive_enabled',
                        e.target.checked,
                      )
                    }
                    data-testid="document-lifecycle-enabled-toggle"
                  />
                  Enabled
                </label>
              </div>

              <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_220px]">
                <FormField
                  label="Archive After"
                  htmlFor="document-lifecycle-value"
                  required
                  error={documentLifecycleErrors.auto_archive_after_value}
                  hint="How long the document can stay active after its latest publish."
                >
                  <input
                    id="document-lifecycle-value"
                    className="input-field"
                    type="number"
                    min={1}
                    max={1200}
                    value={documentLifecycleDraft.auto_archive_after_value}
                    onChange={(e) =>
                      handleDocumentLifecycleFieldChange(
                        'auto_archive_after_value',
                        e.target.value,
                      )
                    }
                    data-testid="document-lifecycle-value"
                  />
                </FormField>

                <FormField label="Unit" htmlFor="document-lifecycle-unit" required>
                  <select
                    id="document-lifecycle-unit"
                    className="select-field"
                    value={documentLifecycleDraft.auto_archive_after_unit}
                    onChange={(e) =>
                      handleDocumentLifecycleFieldChange(
                        'auto_archive_after_unit',
                        e.target.value as ArchiveRetentionUnit,
                      )
                    }
                    data-testid="document-lifecycle-unit"
                  >
                    <option value="days">Days</option>
                    <option value="months">Months</option>
                    <option value="years">Years</option>
                  </select>
                </FormField>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 p-4 space-y-3">
              <div className="font-semibold text-slate-900 dark:text-slate-100">Policy behavior</div>
              <div className="text-sm text-slate-600 dark:text-slate-300">
                The worker checks the latest published version timestamp, not draft edits or view activity.
              </div>
              <div className="text-sm text-slate-600 dark:text-slate-300">
                Deleted documents still follow the separate 30-day recovery window before permanent purge.
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700 dark:border-slate-800 dark:bg-slate-950/50 dark:text-slate-200">
                Current rule:
                {' '}
                {documentLifecycleDraft.auto_archive_enabled
                  ? `Archive after ${documentLifecycleDraft.auto_archive_after_value} ${documentLifecycleDraft.auto_archive_after_unit}`
                  : 'Auto-archive is disabled'}
              </div>
            </div>
          </div>
        )}

        <div className="flex items-center justify-end">
          <SubmitButton
            type="button"
            onClick={handleSaveDocumentLifecycleSettings}
            isLoading={saveDocumentLifecycleMutation.isPending}
            loadingText="Saving..."
            data-testid="document-lifecycle-save"
          >
            Save Document Lifecycle
          </SubmitButton>
        </div>
      </div>

      <div className="surface-card rounded-2xl p-6 space-y-5" data-testid="system-email-settings-section">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-2">
            <div>
              <h2 className="section-title">Email Delivery</h2>
              <p className="body-copy">
                Control the mailbox and sender identity used for invitations and system email.
              </p>
            </div>
            {emailSettingsMetadata ? (
              <div className="grid gap-2 text-sm text-slate-600 dark:text-slate-300 md:grid-cols-2">
                <div>
                  <span className="font-semibold text-slate-800 dark:text-slate-100">Runtime source:</span>{' '}
                  {formatEmailSource(emailSettingsMetadata.source)}
                </div>
                <div>
                  <span className="font-semibold text-slate-800 dark:text-slate-100">Current sender:</span>{' '}
                  {emailSettingsMetadata.settings.from_name} &lt;{emailSettingsMetadata.settings.from_email}&gt;
                </div>
                <div>
                  <span className="font-semibold text-slate-800 dark:text-slate-100">Password:</span>{' '}
                  {emailSettingsMetadata.settings.password_configured
                    ? emailSettingsMetadata.settings.password_masked || 'Configured'
                    : 'Not stored'}
                </div>
                <div>
                  <span className="font-semibold text-slate-800 dark:text-slate-100">Last update:</span>{' '}
                  {emailUpdatedAt || 'Environment-managed'}
                  {emailSettingsMetadata.updated_by ? ` by user #${emailSettingsMetadata.updated_by}` : ''}
                </div>
              </div>
            ) : null}
          </div>
          <div className="rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900 dark:border-blue-900/50 dark:bg-blue-950/30 dark:text-blue-100 lg:max-w-md">
            Leave the password blank to keep the stored secret. Enable <span className="font-semibold">Clear stored password</span> only when you want the database override removed.
          </div>
        </div>

        {isLoading ? (
          <FormSkeleton fields={6} />
        ) : (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 p-4 space-y-4">
              <div className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                <div>
                  <div className="font-semibold text-slate-900 dark:text-slate-100">Email delivery enabled</div>
                  <div className="text-sm text-slate-600 dark:text-slate-300">
                    Disable this to stop outbound invitation and notification email from the app.
                  </div>
                </div>
                <label className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-200">
                  <input
                    type="checkbox"
                    checked={emailSettingsDraft.enabled}
                    onChange={(e) => handleEmailFieldChange('enabled', e.target.checked)}
                    data-testid="email-enabled-toggle"
                  />
                  Enabled
                </label>
              </div>

              <FormField
                label="SMTP Host"
                htmlFor="system-email-host"
                required={emailSettingsDraft.enabled}
                error={emailSettingsErrors.host}
                hint="Example: smtp.gmail.com"
              >
                <input
                  id="system-email-host"
                  className="input-field"
                  value={emailSettingsDraft.host}
                  onChange={(e) => handleEmailFieldChange('host', e.target.value)}
                  placeholder="smtp.example.com"
                  data-testid="system-email-host"
                />
              </FormField>

              <div className="grid gap-4 md:grid-cols-2">
                <FormField label="Port" htmlFor="system-email-port" required error={emailSettingsErrors.port}>
                  <input
                    id="system-email-port"
                    className="input-field"
                    type="number"
                    min={1}
                    max={65535}
                    value={emailSettingsDraft.port}
                    onChange={(e) => handleEmailFieldChange('port', e.target.value)}
                    data-testid="system-email-port"
                  />
                </FormField>

                <FormField label="Security" htmlFor="system-email-security" required>
                  <select
                    id="system-email-security"
                    className="input-field"
                    value={emailSettingsDraft.security}
                    onChange={(e) =>
                      handleEmailFieldChange('security', e.target.value as EmailSecurityMode)
                    }
                    data-testid="system-email-security"
                  >
                    <option value="starttls">STARTTLS</option>
                    <option value="ssl_tls">SSL/TLS</option>
                    <option value="none">No encryption</option>
                  </select>
                </FormField>
              </div>

              <FormField
                label="SMTP Username"
                htmlFor="system-email-username"
                hint="Optional if your provider allows unauthenticated relay."
              >
                <input
                  id="system-email-username"
                  className="input-field"
                  value={emailSettingsDraft.username}
                  onChange={(e) => handleEmailFieldChange('username', e.target.value)}
                  placeholder="mailbox@example.com"
                  data-testid="system-email-username"
                />
              </FormField>
            </div>

            <div className="rounded-xl border border-slate-200 p-4 space-y-4">
              <FormField
                label="Sender Email"
                htmlFor="system-email-from-email"
                required
                error={emailSettingsErrors.from_email}
              >
                <input
                  id="system-email-from-email"
                  className="input-field"
                  type="email"
                  value={emailSettingsDraft.from_email}
                  onChange={(e) => handleEmailFieldChange('from_email', e.target.value)}
                  placeholder="try2@gmail.com"
                  data-testid="system-email-from-email"
                />
              </FormField>

              <FormField
                label="Sender Name"
                htmlFor="system-email-from-name"
                required
                error={emailSettingsErrors.from_name}
              >
                <input
                  id="system-email-from-name"
                  className="input-field"
                  value={emailSettingsDraft.from_name}
                  onChange={(e) => handleEmailFieldChange('from_name', e.target.value)}
                  placeholder="Finale Platform"
                  data-testid="system-email-from-name"
                />
              </FormField>

              <FormField
                label="SMTP Password"
                htmlFor="system-email-password"
                hint={
                  emailSettingsMetadata?.settings.password_configured
                    ? `Stored secret: ${emailSettingsMetadata.settings.password_masked || 'Configured'}`
                    : 'No database password stored yet.'
                }
              >
                <input
                  id="system-email-password"
                  className="input-field"
                  type="password"
                  autoComplete="new-password"
                  value={emailSettingsDraft.password}
                  onChange={(e) => handleEmailFieldChange('password', e.target.value)}
                  placeholder="Leave blank to keep current password"
                  data-testid="system-email-password"
                />
              </FormField>

              <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
                <input
                  type="checkbox"
                  checked={emailSettingsDraft.clear_password}
                  onChange={(e) => handleEmailFieldChange('clear_password', e.target.checked)}
                  data-testid="system-email-clear-password"
                />
                Clear stored password
              </label>
            </div>
          </div>
        )}

        <div className="flex items-center justify-end">
          <SubmitButton
            type="button"
            onClick={handleSaveEmailSettings}
            isLoading={saveEmailSettingsMutation.isPending}
            loadingText="Saving..."
            data-testid="system-email-save"
          >
            Save Email Settings
          </SubmitButton>
        </div>
      </div>

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
                              className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
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
