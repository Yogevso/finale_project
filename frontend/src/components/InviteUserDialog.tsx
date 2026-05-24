import { useId, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { extractApiErrorMessage, useToast } from '@/lib/toast'
import {
  X,
  Mail,
  Building2,
  Send,
  User,
  AlertCircle,
} from 'lucide-react'
import type { UserRole, Company } from '@/types'
import { useFocusTrap } from '@/hooks/useAccessibility'

interface InviteUserDialogProps {
  onClose: () => void
  currentUserRole: UserRole
  currentUserTenantId?: number
  preselectedCompanyId?: number
}

export default function InviteUserDialog({
  onClose,
  currentUserRole,
  currentUserTenantId,
  preselectedCompanyId,
}: InviteUserDialogProps) {
  const titleId = useId()
  const queryClient = useQueryClient()
  const toast = useToast()
  const initialTenantId =
    preselectedCompanyId ??
    (currentUserRole !== 'system_admin' ? (currentUserTenantId ?? '') : '')

  const [formData, setFormData] = useState({
    email: '',
    role: 'customer' as UserRole,
    tenant_id: initialTenantId as number | '',
    message: '',
  })
  const [errors, setErrors] = useState<{
    email?: string
    tenant_id?: string
    submit?: string
  }>({})

  const { containerRef } = useFocusTrap(onClose)

  const { data: companiesData } = useQuery({
    queryKey: ['companies'],
    queryFn: () => api.getCompanies(),
  })

  const companies = companiesData?.items || []
  const selectableCompanies =
    currentUserRole === 'system_admin'
      ? companies
      : companies.filter((company: Company) => company.id === currentUserTenantId)

  const inviteMutation = useMutation({
    mutationFn: () => {
      const effectiveTenantId =
        currentUserRole === 'system_admin'
          ? formData.tenant_id || undefined
          : (currentUserTenantId ?? formData.tenant_id) || undefined

      return api.createInvitation({
        email: formData.email,
        role: formData.role,
        tenant_id: effectiveTenantId,
        message: formData.message || undefined,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations'] })
      toast.success('Invitation sent', 'The user will receive an invitation email shortly.')
      onClose()
    },
    onError: (err: unknown) => {
      const message = extractApiErrorMessage(err, 'Failed to send invitation')
      setErrors((current) => ({ ...current, submit: message }))
      toast.error('Failed to send invitation', message)
    },
  })

  const roles: UserRole[] = ['system_admin', 'admin', 'manager', 'editor', 'viewer', 'customer']

  // Filter available roles based on current user's role
  const availableRoles = roles.filter((role) => {
    if (currentUserRole === 'system_admin') return true
    if (currentUserRole === 'admin') return role !== 'system_admin'
    if (currentUserRole === 'manager') return ['editor', 'viewer', 'customer'].includes(role)
    return false
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setErrors({})
    const effectiveTenantId =
      currentUserRole === 'system_admin'
        ? formData.tenant_id || undefined
        : (currentUserTenantId ?? formData.tenant_id) || undefined

    const trimmedEmail = formData.email.trim()
    if (!trimmedEmail) {
      setErrors({ email: 'Email is required' })
      return
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      setErrors({ email: 'Enter a valid email address' })
      return
    }

    if (formData.role === 'customer' && !effectiveTenantId) {
      setErrors({ tenant_id: 'Customers must be assigned to a company' })
      return
    }

    inviteMutation.mutate()
  }

  return (
    <div className="modal-overlay flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0"
        onClick={onClose}
        aria-label="Close invite dialog"
        tabIndex={-1}
      />
      <div ref={containerRef} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1} className="modal-content motion-enter-scale relative z-10 w-full max-w-md dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-200 p-6 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-xl">
              <Mail className="w-5 h-5 text-blue-600" />
            </div>
            <h2 id={titleId} className="text-lg font-semibold text-slate-900 font-display dark:text-slate-100">Invite User</h2>
          </div>
          <button type="button" onClick={onClose} className="rounded-full p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:text-slate-500 dark:hover:bg-slate-800 dark:hover:text-slate-200" aria-label="Close invite dialog">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {errors.submit && (
            <div id="invite-error" role="alert" className="flex items-center gap-2 p-3 bg-rose-50 text-rose-700 rounded-xl border border-rose-200">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm">{errors.submit}</span>
            </div>
          )}

          <div>
            <label htmlFor="invite-email" className="block text-sm font-medium text-slate-700 mb-1">
              Email Address <span className="text-rose-500">*</span>
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                id="invite-email"
                type="email"
                value={formData.email}
                onChange={(e) => {
                  setFormData({ ...formData, email: e.target.value })
                  setErrors((current) => ({ ...current, email: undefined, submit: undefined }))
                }}
                placeholder="user@example.com"
                required
                className="input-field pl-10"
                aria-invalid={!!errors.email}
                aria-describedby={errors.email ? 'invite-email-error' : errors.submit ? 'invite-error' : undefined}
              />
            </div>
            {errors.email ? (
              <p id="invite-email-error" role="alert" className="mt-1 text-sm text-rose-500">
                {errors.email}
              </p>
            ) : null}
          </div>

          <div>
            <label htmlFor="invite-role" className="block text-sm font-medium text-slate-700 mb-1">
              Role <span className="text-rose-500">*</span>
            </label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <select
                id="invite-role"
                value={formData.role}
                onChange={(e) => setFormData({ ...formData, role: e.target.value as UserRole })}
                className="select-field pl-10 appearance-none"
              >
                {availableRoles.map((role) => (
                  <option key={role} value={role}>
                    {role.replace('_', ' ')}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Show company selector for customer role */}
          {(formData.role === 'customer' || preselectedCompanyId) && (
            <div>
              <label htmlFor="invite-company" className="block text-sm font-medium text-slate-700 mb-1">
                Company <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <select
                  id="invite-company"
                  value={formData.tenant_id}
                  onChange={(e) => {
                    setFormData({
                      ...formData,
                      tenant_id: e.target.value ? Number(e.target.value) : '',
                    })
                    setErrors((current) => ({ ...current, tenant_id: undefined, submit: undefined }))
                  }}
                  required={formData.role === 'customer'}
                  disabled={!!preselectedCompanyId || currentUserRole !== 'system_admin'}
                  className="select-field pl-10 appearance-none disabled:bg-slate-100"
                  aria-invalid={!!errors.tenant_id}
                  aria-describedby={errors.tenant_id ? 'invite-company-error' : undefined}
                >
                  <option value="">Select Company</option>
                  {selectableCompanies.map((company: Company) => (
                    <option key={company.id} value={company.id}>
                      {company.name}
                    </option>
                  ))}
                </select>
              </div>
              {formData.role === 'customer' && (
                <p className="text-xs text-slate-500 mt-1">
                  Customers must be assigned to a company
                </p>
              )}
              {errors.tenant_id ? (
                <p id="invite-company-error" role="alert" className="mt-1 text-sm text-rose-500">
                  {errors.tenant_id}
                </p>
              ) : null}
              {currentUserRole !== 'system_admin' && (
                <p className="text-xs text-slate-500 mt-1">
                  Invitations are scoped to your company.
                </p>
              )}
            </div>
          )}

          <div>
            <label htmlFor="invite-message" className="block text-sm font-medium text-slate-700 mb-1">
              Message (optional)
            </label>
            <textarea
              id="invite-message"
              value={formData.message}
              onChange={(e) => setFormData({ ...formData, message: e.target.value })}
              placeholder="Add a personal message to include in the invitation email..."
              rows={3}
              maxLength={1000}
              className="input-field resize-none"
            />
            <p className="text-xs text-slate-400 mt-1 text-right">
              {formData.message.length}/1000
            </p>
          </div>

          <div className="bg-blue-50 rounded-2xl p-4 border border-blue-200">
            <p className="text-sm text-blue-800">
              <strong>Note:</strong> The invitation will be valid for 7 days. The user will
              receive an email with a link to create their account.
            </p>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="btn-ghost"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={inviteMutation.isPending}
              className="btn-primary disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
              {inviteMutation.isPending ? 'Sending...' : 'Send Invitation'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
