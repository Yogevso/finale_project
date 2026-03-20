import { useCallback, useEffect, useState } from 'react'
import { Download, Plus, Settings } from 'lucide-react'
import { api } from '@/lib/api'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { FormField, PasswordInput, SubmitButton } from '@/components/form'
import { ListSkeleton } from '@/components/skeletons'
import { extractApiErrorMessage } from '@/lib/toast'
import type { TenantQuota } from '@/lib/api/adminOpsApi'
import { toast } from 'sonner'
import type { Tenant } from './types'

const emptyProvisionForm = {
  tenant_name: '',
  tenant_slug: '',
  admin_username: '',
  admin_email: '',
  admin_password: '',
  company_type: 'customer',
  contact_email: '',
}

type ProvisionFormErrors = Partial<Record<keyof typeof emptyProvisionForm, string>>
type QuotaFieldErrors = {
  max_users?: string
  max_documents?: string
  max_storage_mb?: string
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const TENANT_SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/

export default function TenantManagementPanel() {
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [quota, setQuota] = useState<TenantQuota | null>(null)
  const [loading, setLoading] = useState(true)
  const [hasError, setHasError] = useState(false)
  const [showProvision, setShowProvision] = useState(false)
  const [provForm, setProvForm] = useState(emptyProvisionForm)
  const [provErrors, setProvErrors] = useState<ProvisionFormErrors>({})
  const [quotaErrors, setQuotaErrors] = useState<QuotaFieldErrors>({})
  const [isProvisioning, setIsProvisioning] = useState(false)
  const [isSavingQuota, setIsSavingQuota] = useState(false)

  const loadTenants = useCallback(() => {
    setHasError(false)
    setLoading(true)
    api.getCompanies({ per_page: 100 })
      .then((response) => {
        setTenants(response.items.map((company) => ({
          id: company.id,
          name: company.name,
          slug: company.slug,
          is_active: company.is_active,
        })))
      })
      .catch(() => setHasError(true))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadTenants()
  }, [loadTenants])

  useEffect(() => {
    if (selected) {
      api.getTenantQuota(selected).then(setQuota).catch(() => setQuota(null))
      setQuotaErrors({})
    }
  }, [selected])

  const clearProvisionError = (field: keyof typeof emptyProvisionForm) => {
    if (!provErrors[field]) {
      return
    }

    setProvErrors((current) => ({
      ...current,
      [field]: undefined,
    }))
  }

  const clearQuotaError = (field: keyof QuotaFieldErrors) => {
    if (!quotaErrors[field]) {
      return
    }

    setQuotaErrors((current) => ({
      ...current,
      [field]: undefined,
    }))
  }

  const handleSuspend = async (id: number) => {
    const reason = prompt('Suspension reason:')
    if (reason === null) return
    try {
      await api.suspendTenant(id, reason || undefined)
      setTenants((current) => current.map((tenant) => (
        tenant.id === id ? { ...tenant, is_active: false } : tenant
      )))
      toast.success('Tenant suspended')
    } catch (error: unknown) {
      toast.error(extractApiErrorMessage(error, 'Suspension failed'))
    }
  }

  const handleReactivate = async (id: number) => {
    try {
      await api.reactivateTenant(id)
      setTenants((current) => current.map((tenant) => (
        tenant.id === id ? { ...tenant, is_active: true } : tenant
      )))
      toast.success('Tenant reactivated')
    } catch (error: unknown) {
      toast.error(extractApiErrorMessage(error, 'Reactivation failed'))
    }
  }

  const handleExport = async (id: number) => {
    try {
      const exportPayload = await api.exportTenantData(id)
      const blob = new Blob([JSON.stringify(exportPayload.export_data, null, 2)], { type: 'application/json' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `tenant-${id}-export.json`
      link.click()
      URL.revokeObjectURL(link.href)
      toast.success('Export downloaded')
    } catch {
      toast.error('Export failed')
    }
  }

  const handleProvision = async () => {
    const nextErrors: ProvisionFormErrors = {}
    const trimmedName = provForm.tenant_name.trim()
    const trimmedSlug = provForm.tenant_slug.trim()
    const trimmedUsername = provForm.admin_username.trim()
    const trimmedAdminEmail = provForm.admin_email.trim()
    const trimmedPassword = provForm.admin_password.trim()
    const trimmedContactEmail = provForm.contact_email.trim()

    if (!trimmedName) {
      nextErrors.tenant_name = 'Tenant name is required.'
    }

    if (!trimmedSlug) {
      nextErrors.tenant_slug = 'Tenant slug is required.'
    } else if (!TENANT_SLUG_PATTERN.test(trimmedSlug)) {
      nextErrors.tenant_slug = 'Use lowercase letters, numbers, and hyphens only.'
    }

    if (!trimmedUsername) {
      nextErrors.admin_username = 'Admin username is required.'
    }

    if (!trimmedAdminEmail) {
      nextErrors.admin_email = 'Admin email is required.'
    } else if (!EMAIL_PATTERN.test(trimmedAdminEmail)) {
      nextErrors.admin_email = 'Enter a valid email address.'
    }

    if (!trimmedPassword) {
      nextErrors.admin_password = 'Admin password is required.'
    } else if (trimmedPassword.length < 8) {
      nextErrors.admin_password = 'Use at least 8 characters.'
    }

    if (trimmedContactEmail && !EMAIL_PATTERN.test(trimmedContactEmail)) {
      nextErrors.contact_email = 'Enter a valid email address.'
    }

    if (Object.values(nextErrors).some(Boolean)) {
      setProvErrors(nextErrors)
      return
    }

    setProvErrors({})
    setIsProvisioning(true)
    try {
      const result = await api.provisionTenant({
        ...provForm,
        tenant_name: trimmedName,
        tenant_slug: trimmedSlug,
        admin_username: trimmedUsername,
        admin_email: trimmedAdminEmail,
        admin_password: trimmedPassword,
        contact_email: trimmedContactEmail,
      })
      toast.success(`Tenant "${result.tenant_name}" created with admin "${result.admin_username}"`)
      setShowProvision(false)
      setProvForm(emptyProvisionForm)
      setProvErrors({})
      loadTenants()
    } catch (error: unknown) {
      toast.error(extractApiErrorMessage(error, 'Provisioning failed'))
    } finally {
      setIsProvisioning(false)
    }
  }

  const handleQuotaSave = async () => {
    if (!selected || !quota) return

    const nextErrors: QuotaFieldErrors = {}
    ;(['max_users', 'max_documents', 'max_storage_mb'] as const).forEach((field) => {
      const value = quota[field]
      if (
        value !== null &&
        value !== undefined &&
        (!Number.isFinite(value) || value < 0 || !Number.isInteger(value))
      ) {
        nextErrors[field] = 'Use a whole number of 0 or greater.'
      }
    })

    if (Object.values(nextErrors).some(Boolean)) {
      setQuotaErrors(nextErrors)
      return
    }

    setQuotaErrors({})
    setIsSavingQuota(true)
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
    } finally {
      setIsSavingQuota(false)
    }
  }

  if (loading) return <ListSkeleton rows={6} />

  if (hasError) {
    return (
      <ErrorState
        title="Tenant management unavailable"
        message="We could not load the tenant roster."
        onRetry={loadTenants}
      />
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Tenants</h2>
        <button
          type="button"
          onClick={() => {
            setShowProvision((current) => !current)
            setProvErrors({})
          }}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700"
        >
          <Plus size={16} />
          Provision Tenant
        </button>
      </div>

      {showProvision ? (
        <div className="space-y-4 rounded-xl border bg-white p-6">
          <h3 className="font-semibold">New Tenant Provisioning</h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <FormField
              label="Tenant name"
              htmlFor="tenant-provision-name"
              required
              error={provErrors.tenant_name}
            >
              <input
                id="tenant-provision-name"
                placeholder="Tenant Name"
                value={provForm.tenant_name}
                onChange={(event) => {
                  setProvForm((form) => ({ ...form, tenant_name: event.target.value }))
                  clearProvisionError('tenant_name')
                }}
                className="input-field"
                aria-invalid={provErrors.tenant_name ? true : undefined}
              />
            </FormField>
            <FormField
              label="Tenant slug"
              htmlFor="tenant-provision-slug"
              required
              error={provErrors.tenant_slug}
              hint="Lowercase letters, numbers, and hyphens only."
            >
              <input
                id="tenant-provision-slug"
                placeholder="Slug (lowercase, hyphens)"
                value={provForm.tenant_slug}
                onChange={(event) => {
                  setProvForm((form) => ({ ...form, tenant_slug: event.target.value }))
                  clearProvisionError('tenant_slug')
                }}
                className="input-field"
                aria-invalid={provErrors.tenant_slug ? true : undefined}
              />
            </FormField>
            <FormField
              label="Admin username"
              htmlFor="tenant-provision-admin-username"
              required
              error={provErrors.admin_username}
            >
              <input
                id="tenant-provision-admin-username"
                placeholder="Admin Username"
                value={provForm.admin_username}
                onChange={(event) => {
                  setProvForm((form) => ({ ...form, admin_username: event.target.value }))
                  clearProvisionError('admin_username')
                }}
                className="input-field"
                aria-invalid={provErrors.admin_username ? true : undefined}
              />
            </FormField>
            <FormField
              label="Admin email"
              htmlFor="tenant-provision-admin-email"
              required
              error={provErrors.admin_email}
            >
              <input
                id="tenant-provision-admin-email"
                placeholder="Admin Email"
                type="email"
                value={provForm.admin_email}
                onChange={(event) => {
                  setProvForm((form) => ({ ...form, admin_email: event.target.value }))
                  clearProvisionError('admin_email')
                }}
                className="input-field"
                aria-invalid={provErrors.admin_email ? true : undefined}
              />
            </FormField>
            <PasswordInput
              id="tenant-provision-admin-password"
              label="Admin password"
              value={provForm.admin_password}
              onChange={(event) => {
                setProvForm((form) => ({ ...form, admin_password: event.target.value }))
                clearProvisionError('admin_password')
              }}
              error={provErrors.admin_password}
              hint="Use at least 8 characters."
              required
              wrapperClassName="md:col-span-2"
            />
            <FormField
              label="Contact email"
              htmlFor="tenant-provision-contact-email"
              error={provErrors.contact_email}
              hint="Optional"
              className="md:col-span-2"
            >
              <input
                id="tenant-provision-contact-email"
                placeholder="Contact Email"
                type="email"
                value={provForm.contact_email}
                onChange={(event) => {
                  setProvForm((form) => ({ ...form, contact_email: event.target.value }))
                  clearProvisionError('contact_email')
                }}
                className="input-field"
                aria-invalid={provErrors.contact_email ? true : undefined}
              />
            </FormField>
          </div>
          <div className="flex gap-2">
            <SubmitButton
              type="button"
              onClick={() => void handleProvision()}
              isLoading={isProvisioning}
              loadingText="Creating..."
            >
              Create
            </SubmitButton>
            <button
              type="button"
              onClick={() => {
                setShowProvision(false)
                setProvErrors({})
              }}
              className="btn-ghost"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}

      {tenants.length === 0 ? (
        <EmptyState
          icon={<Settings className="h-8 w-8" aria-hidden="true" />}
          title="No tenants found"
          description="Provision a tenant to start configuring quotas and access."
          action={{ label: 'Provision Tenant', onClick: () => setShowProvision(true) }}
        />
      ) : (
        <div className="divide-y rounded-xl border bg-white">
          {tenants.map((tenant) => (
            <div
              key={tenant.id}
              className={`flex cursor-pointer items-center justify-between p-4 hover:bg-slate-50 ${selected === tenant.id ? 'bg-indigo-50' : ''}`}
              onClick={() => setSelected(selected === tenant.id ? null : tenant.id)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  setSelected(selected === tenant.id ? null : tenant.id)
                }
              }}
              role="button"
              tabIndex={0}
              aria-pressed={selected === tenant.id}
            >
              <div>
                <p className="font-medium">{tenant.name}</p>
                <p className="text-xs text-slate-500">{tenant.slug} | ID: {tenant.id}</p>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs ${
                    tenant.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                  }`}
                >
                  {tenant.is_active ? 'Active' : 'Suspended'}
                </span>
                {tenant.is_active ? (
                  <button type="button" onClick={(event) => { event.stopPropagation(); void handleSuspend(tenant.id) }} className="rounded-lg border px-3 py-1 text-xs text-red-600 hover:bg-red-50">
                    Suspend
                  </button>
                ) : (
                  <button type="button" onClick={(event) => { event.stopPropagation(); void handleReactivate(tenant.id) }} className="rounded-lg border px-3 py-1 text-xs text-green-600 hover:bg-green-50">
                    Reactivate
                  </button>
                )}
                <button type="button" onClick={(event) => { event.stopPropagation(); void handleExport(tenant.id) }} className="rounded-lg border px-3 py-1 text-xs text-slate-600 hover:bg-slate-50" title="Export" aria-label={`Export data for ${tenant.name}`}>
                  <Download size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {selected && quota ? (
        <div className="space-y-4 rounded-xl border bg-white p-6">
          <h3 className="font-semibold">Quota - Tenant #{selected}</h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <FormField
              label="Max users"
              htmlFor="tenant-quota-max-users"
              error={quotaErrors.max_users}
              hint={`Current: ${quota.current_users}`}
            >
              <input
                id="tenant-quota-max-users"
                type="number"
                min="0"
                step="1"
                value={quota.max_users ?? ''}
                onChange={(event) => {
                  setQuota((current) =>
                    current
                      ? {
                          ...current,
                          max_users: event.target.value ? Number(event.target.value) : null,
                        }
                      : current,
                  )
                  clearQuotaError('max_users')
                }}
                className="input-field"
                aria-invalid={quotaErrors.max_users ? true : undefined}
              />
            </FormField>
            <FormField
              label="Max documents"
              htmlFor="tenant-quota-max-documents"
              error={quotaErrors.max_documents}
              hint={`Current: ${quota.current_documents}`}
            >
              <input
                id="tenant-quota-max-documents"
                type="number"
                min="0"
                step="1"
                value={quota.max_documents ?? ''}
                onChange={(event) => {
                  setQuota((current) =>
                    current
                      ? {
                          ...current,
                          max_documents: event.target.value ? Number(event.target.value) : null,
                        }
                      : current,
                  )
                  clearQuotaError('max_documents')
                }}
                className="input-field"
                aria-invalid={quotaErrors.max_documents ? true : undefined}
              />
            </FormField>
            <FormField
              label="Max storage (MB)"
              htmlFor="tenant-quota-max-storage"
              error={quotaErrors.max_storage_mb}
              hint="Use a whole number of megabytes."
            >
              <input
                id="tenant-quota-max-storage"
                type="number"
                min="0"
                step="1"
                value={quota.max_storage_mb ?? ''}
                onChange={(event) => {
                  setQuota((current) =>
                    current
                      ? {
                          ...current,
                          max_storage_mb: event.target.value ? Number(event.target.value) : null,
                        }
                      : current,
                  )
                  clearQuotaError('max_storage_mb')
                }}
                className="input-field"
                aria-invalid={quotaErrors.max_storage_mb ? true : undefined}
              />
            </FormField>
          </div>
          <SubmitButton
            type="button"
            onClick={() => void handleQuotaSave()}
            isLoading={isSavingQuota}
            loadingText="Saving..."
          >
            Save Quota
          </SubmitButton>
        </div>
      ) : null}
    </div>
  )
}
