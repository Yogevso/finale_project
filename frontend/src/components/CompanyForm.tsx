import { useId, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { X } from 'lucide-react'
import type { Company, CompanyCreate, CompanyUpdate, CompanyType } from '@/types'
import { useFocusTrap } from '@/hooks/useAccessibility'

interface CompanyFormProps {
  company?: Company | null
  onClose: () => void
  onSuccess: () => void
}

export default function CompanyForm({ company, onClose, onSuccess }: CompanyFormProps) {
  const isEditing = !!company
  const titleId = useId()
  
  const [formData, setFormData] = useState<CompanyCreate>({
    name: company?.name || '',
    slug: company?.slug || '',
    contact_email: company?.contact_email || '',
    company_type: company?.company_type || 'customer',
    company_logo: company?.company_logo || '',
    is_active: company?.is_active ?? true,
  })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const { containerRef } = useFocusTrap(onClose)

  const createMutation = useMutation({
    mutationFn: (data: CompanyCreate) => api.createCompany(data),
    onSuccess: () => {
      onSuccess()
    },
    onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
      setErrors({ submit: err.response?.data?.detail || 'Failed to create company' })
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: CompanyUpdate) => api.updateCompany(company!.id, data),
    onSuccess: () => {
      onSuccess()
    },
    onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
      setErrors({ submit: err.response?.data?.detail || 'Failed to update company' })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setErrors({})

    // Basic validation
    if (!formData.name.trim()) {
      setErrors({ name: 'Company name is required' })
      return
    }

    if (formData.contact_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.contact_email)) {
      setErrors({ contact_email: 'Invalid email format' })
      return
    }

    if (isEditing) {
      updateMutation.mutate(formData)
    } else {
      createMutation.mutate(formData)
    }
  }

  const isLoading = createMutation.isPending || updateMutation.isPending

  return (
    <div className="modal-overlay flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0"
        onClick={onClose}
        aria-label="Close company form"
        tabIndex={-1}
      />
      <div ref={containerRef} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1} className="modal-content motion-enter-scale relative w-full max-w-lg dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-200 p-4 dark:border-slate-800">
          <h2 id={titleId} className="text-lg font-semibold text-slate-900 font-display dark:text-slate-100">
            {isEditing ? 'Edit Company' : 'Create New Company'}
          </h2>
          <button type="button" onClick={onClose} className="rounded-full p-2 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Close company form">
            <X className="w-5 h-5 text-slate-500 dark:text-slate-400" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {errors.submit && (
            <div role="alert" aria-live="assertive" className="p-3 bg-rose-50 text-rose-700 rounded-xl border border-rose-200 text-sm">
              {errors.submit}
            </div>
          )}

          <div>
            <label htmlFor="company-name" className="block text-sm font-medium text-slate-700 mb-1">
              Company Name *
            </label>
            <input
              id="company-name"
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className={`input-field ${
                errors.name ? 'border-rose-500 focus:ring-rose-500 motion-error-shake' : ''
              }`}
              placeholder="Acme Corporation"
              aria-invalid={!!errors.name}
              aria-describedby={errors.name ? 'company-name-error' : undefined}
            />
            {errors.name && <p id="company-name-error" role="alert" className="mt-1 text-sm text-rose-500">{errors.name}</p>}
          </div>

          <div>
            <label htmlFor="company-slug" className="block text-sm font-medium text-slate-700 mb-1">
              Slug
            </label>
            <input
              id="company-slug"
              type="text"
              value={formData.slug}
              onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
              className="input-field"
              placeholder="acme-corp (auto-generated if empty)"
              pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
            />
            <p className="mt-1 text-xs text-slate-500">
              URL-friendly identifier — lowercase letters, numbers, and hyphens only. Leave empty to auto-generate from name.
            </p>
          </div>

          <div>
            <label htmlFor="company-contact-email" className="block text-sm font-medium text-slate-700 mb-1">
              Contact Email
            </label>
            <input
              id="company-contact-email"
              type="email"
              value={formData.contact_email}
              onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
              className={`input-field ${
                errors.contact_email ? 'border-rose-500 focus:ring-rose-500 motion-error-shake' : ''
              }`}
              placeholder="contact@acme.com"
              aria-invalid={!!errors.contact_email}
              aria-describedby={errors.contact_email ? 'company-contact-email-error' : undefined}
            />
            {errors.contact_email && <p id="company-contact-email-error" role="alert" className="mt-1 text-sm text-rose-500">{errors.contact_email}</p>}
          </div>

          <div>
            <label htmlFor="company-type" className="block text-sm font-medium text-slate-700 mb-1">
              Company Type
            </label>
            <select
              id="company-type"
              value={formData.company_type}
              onChange={(e) => setFormData({ ...formData, company_type: e.target.value as CompanyType })}
              className="select-field"
            >
              <option value="customer">Customer</option>
              <option value="partner">Partner</option>
              <option value="internal">Internal</option>
            </select>
          </div>

          <div>
            <label htmlFor="company-logo-url" className="block text-sm font-medium text-slate-700 mb-1">
              Company Logo URL
            </label>
            <input
              id="company-logo-url"
              type="url"
              value={formData.company_logo}
              onChange={(e) => setFormData({ ...formData, company_logo: e.target.value })}
              className="input-field"
              placeholder="https://example.com/logo.png"
            />
            <p className="mt-1 text-xs text-slate-500">
              Full URL to an image (PNG, SVG, or JPG recommended).
            </p>
            {formData.company_logo && /^https?:\/\/.+/i.test(formData.company_logo) && (
              <img
                src={formData.company_logo}
                alt="Logo preview"
                className="mt-2 h-10 w-10 rounded object-contain border border-slate-200"
                decoding="async"
                height={40}
                loading="lazy"
                width={40}
                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
              />
            )}
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_active"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="w-4 h-4 text-sky-600 border-slate-300 rounded focus:ring-sky-500"
            />
            <label htmlFor="is_active" className="text-sm text-slate-700">
              Active
            </label>
          </div>

          <div className="flex justify-end gap-3 border-t border-slate-200 pt-4 dark:border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="btn-ghost"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary disabled:opacity-50"
            >
              {isLoading ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Company'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
