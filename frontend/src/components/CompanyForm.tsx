import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { X } from 'lucide-react'
import type { Company, CompanyCreate, CompanyUpdate, CompanyType } from '@/types'

interface CompanyFormProps {
  company?: Company | null
  onClose: () => void
  onSuccess: () => void
}

export default function CompanyForm({ company, onClose, onSuccess }: CompanyFormProps) {
  const isEditing = !!company
  
  const [formData, setFormData] = useState<CompanyCreate>({
    name: company?.name || '',
    slug: company?.slug || '',
    contact_email: company?.contact_email || '',
    company_type: company?.company_type || 'customer',
    company_logo: company?.company_logo || '',
    is_active: company?.is_active ?? true,
  })
  const [errors, setErrors] = useState<Record<string, string>>({})

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
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4">
        <div className="flex items-center justify-between p-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900 font-display">
            {isEditing ? 'Edit Company' : 'Create New Company'}
          </h2>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-full">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {errors.submit && (
            <div className="p-3 bg-rose-50 text-rose-700 rounded-xl border border-rose-200 text-sm">
              {errors.submit}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Company Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className={`input-field ${
                errors.name ? 'border-rose-500 focus:ring-rose-500' : ''
              }`}
              placeholder="Acme Corporation"
            />
            {errors.name && <p className="mt-1 text-sm text-rose-500">{errors.name}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Slug
            </label>
            <input
              type="text"
              value={formData.slug}
              onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
              className="input-field"
              placeholder="acme-corp (auto-generated if empty)"
            />
            <p className="mt-1 text-xs text-slate-500">
              URL-friendly identifier. Leave empty to auto-generate from name.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Contact Email
            </label>
            <input
              type="email"
              value={formData.contact_email}
              onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
              className={`input-field ${
                errors.contact_email ? 'border-rose-500 focus:ring-rose-500' : ''
              }`}
              placeholder="contact@acme.com"
            />
            {errors.contact_email && <p className="mt-1 text-sm text-rose-500">{errors.contact_email}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Company Type
            </label>
            <select
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
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Company Logo URL
            </label>
            <input
              type="url"
              value={formData.company_logo}
              onChange={(e) => setFormData({ ...formData, company_logo: e.target.value })}
              className="input-field"
              placeholder="https://example.com/logo.png"
            />
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

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
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
