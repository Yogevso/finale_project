import { useId, useState } from 'react'
import { X } from 'lucide-react'

import { useFocusTrap } from '@/hooks/useAccessibility'
import { validateForm, type FieldErrors } from '@/lib/validation'
import { userCreateSchema, userUpdateSchema } from '@/lib/validation/schemas'
import type { Company, User, UserRole } from '@/types'

import { ALL_USER_ROLES } from '../constants'
import type { UserFormSubmission } from '../types'

interface UserFormDialogProps {
  title: string
  user?: User
  companies: Company[]
  currentUserRole: UserRole
  onSubmit: (data: UserFormSubmission) => void
  onClose: () => void
  isLoading: boolean
}

export function UserFormDialog({
  title,
  user,
  companies,
  currentUserRole,
  onSubmit,
  onClose,
  isLoading,
}: UserFormDialogProps) {
  const titleId = useId()
  const { containerRef } = useFocusTrap(onClose)
  const [formData, setFormData] = useState({
    email: user?.email ?? '',
    username: user?.username ?? '',
    full_name: user?.full_name ?? '',
    password: '',
    role: (user?.role ?? 'viewer') as UserRole,
    tenant_id: (user?.tenant_id ?? '') as number | '',
    is_active: user?.is_active ?? true,
  })
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})

  const isEdit = !!user
  const initialTenantId = user?.tenant_id ?? ''
  const availableRoles = ALL_USER_ROLES.filter((role) => {
    if (currentUserRole === 'system_admin') return true
    if (currentUserRole === 'admin') return role !== 'system_admin'
    if (currentUserRole === 'manager') return ['editor', 'viewer', 'customer'].includes(role)
    return false
  })

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    setFieldErrors({})

    if (isEdit && user) {
      const updates = {
        email: formData.email !== user.email ? formData.email : undefined,
        full_name: formData.full_name !== user.full_name ? formData.full_name : undefined,
        role: formData.role !== user.role ? formData.role : undefined,
      }
      const result = validateForm(userUpdateSchema, updates)
      if (result.errors) {
        setFieldErrors(result.errors)
        return
      }

      onSubmit({
        ...updates,
        is_active: formData.is_active !== user.is_active ? formData.is_active : undefined,
        tenant_id:
          formData.tenant_id !== initialTenantId
            ? formData.tenant_id === ''
              ? null
              : Number(formData.tenant_id)
            : undefined,
      })
      return
    }

    const result = validateForm(userCreateSchema, {
      username: formData.username,
      email: formData.email,
      full_name: formData.full_name,
      password: formData.password,
      role: formData.role,
    })
    if (result.errors) {
      setFieldErrors(result.errors)
      return
    }

    onSubmit({
      email: formData.email,
      username: formData.username,
      full_name: formData.full_name,
      password: formData.password,
      role: formData.role,
      tenant_id: formData.tenant_id === '' ? undefined : Number(formData.tenant_id),
    })
  }

  return (
    <div className="modal-overlay flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0"
        onClick={onClose}
        aria-label={`Close ${title} dialog`}
        tabIndex={-1}
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="modal-content relative w-full max-w-md"
      >
        <div className="flex items-center justify-between border-b border-slate-200 p-6 dark:border-slate-800">
          <h2
            id={titleId}
            className="text-lg font-display font-semibold text-slate-900 dark:text-slate-100"
          >
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-200"
            aria-label={`Close ${title} dialog`}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 p-6">
          {Object.keys(fieldErrors).length > 0 ? (
            <div
              role="alert"
              className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700"
            >
              {Object.values(fieldErrors)[0]}
            </div>
          ) : null}

          {!isEdit ? (
            <>
              <div>
                <label
                  htmlFor="user-form-username"
                  className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200"
                >
                  Username
                </label>
                <input
                  id="user-form-username"
                  type="text"
                  value={formData.username}
                  onChange={(event) =>
                    setFormData((current) => ({ ...current, username: event.target.value }))
                  }
                  required
                  minLength={3}
                  className="input-field"
                />
              </div>
              <div>
                <label
                  htmlFor="user-form-password"
                  className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200"
                >
                  Password
                </label>
                <input
                  id="user-form-password"
                  type="password"
                  value={formData.password}
                  onChange={(event) =>
                    setFormData((current) => ({ ...current, password: event.target.value }))
                  }
                  required
                  minLength={8}
                  className="input-field"
                />
              </div>
            </>
          ) : null}

          <div>
            <label
              htmlFor="user-form-email"
              className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200"
            >
              Email
            </label>
            <input
              id="user-form-email"
              type="email"
              value={formData.email}
              onChange={(event) =>
                setFormData((current) => ({ ...current, email: event.target.value }))
              }
              required
              className="input-field"
            />
          </div>

          <div>
            <label
              htmlFor="user-form-full-name"
              className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200"
            >
              Full Name
            </label>
            <input
              id="user-form-full-name"
              type="text"
              value={formData.full_name}
              onChange={(event) =>
                setFormData((current) => ({ ...current, full_name: event.target.value }))
              }
              required
              className="input-field"
            />
          </div>

          <div>
            <label
              htmlFor="user-form-role"
              className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200"
            >
              Role
            </label>
            <select
              id="user-form-role"
              value={formData.role}
              onChange={(event) =>
                setFormData((current) => ({ ...current, role: event.target.value as UserRole }))
              }
              className="select-field"
            >
              {availableRoles.map((role) => (
                <option key={role} value={role}>
                  {role.replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>

          {(formData.role === 'customer' || user?.role === 'customer') ? (
            <div>
              <label
                htmlFor="user-form-company"
                className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200"
              >
                Company <span className="text-rose-500">*</span>
              </label>
              <select
                id="user-form-company"
                value={formData.tenant_id}
                onChange={(event) =>
                  setFormData((current) => ({
                    ...current,
                    tenant_id: event.target.value ? Number(event.target.value) : '',
                  }))
                }
                required={formData.role === 'customer'}
                className="select-field"
              >
                <option value="">Select Company</option>
                {companies.map((company) => (
                  <option key={company.id} value={company.id}>
                    {company.name}
                  </option>
                ))}
              </select>
              {formData.role === 'customer' ? (
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Customers must be assigned to a company
                </p>
              ) : null}
            </div>
          ) : null}

          {isEdit ? (
            <div className="flex items-center gap-2">
              <input
                id="user-form-active"
                type="checkbox"
                checked={formData.is_active}
                onChange={(event) =>
                  setFormData((current) => ({ ...current, is_active: event.target.checked }))
                }
                className="rounded border-slate-300"
              />
              <label
                htmlFor="user-form-active"
                className="text-sm text-slate-700 dark:text-slate-200"
              >
                Active
              </label>
            </div>
          ) : null}

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100"
            >
              Cancel
            </button>
            <button type="submit" disabled={isLoading} className="btn-primary">
              {isLoading ? 'Saving...' : isEdit ? 'Save Changes' : 'Create User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
