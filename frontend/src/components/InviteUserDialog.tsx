import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import {
  X,
  Mail,
  Building2,
  Send,
  User,
  AlertCircle,
} from 'lucide-react'
import type { UserRole, Company } from '@/types'

interface InviteUserDialogProps {
  onClose: () => void
  currentUserRole: UserRole
  preselectedCompanyId?: number
}

export default function InviteUserDialog({
  onClose,
  currentUserRole,
  preselectedCompanyId,
}: InviteUserDialogProps) {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState({
    email: '',
    role: 'customer' as UserRole,
    tenant_id: preselectedCompanyId || ('' as number | ''),
    message: '',
  })
  const [error, setError] = useState('')

  const { data: companiesData } = useQuery({
    queryKey: ['companies'],
    queryFn: () => api.getCompanies(),
  })

  const companies = companiesData?.items || []

  const inviteMutation = useMutation({
    mutationFn: () =>
      api.createInvitation({
        email: formData.email,
        role: formData.role,
        tenant_id: formData.tenant_id || undefined,
        message: formData.message || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations'] })
      onClose()
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to send invitation')
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
    setError('')

    if (!formData.email) {
      setError('Email is required')
      return
    }

    if (formData.role === 'customer' && !formData.tenant_id) {
      setError('Customers must be assigned to a company')
      return
    }

    inviteMutation.mutate()
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Mail className="w-5 h-5 text-blue-600" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900">Invite User</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 text-red-700 rounded-lg">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email Address <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="user@example.com"
                required
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Role <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <select
                value={formData.role}
                onChange={(e) => setFormData({ ...formData, role: e.target.value as UserRole })}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none"
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
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Company <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <select
                  value={formData.tenant_id}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      tenant_id: e.target.value ? Number(e.target.value) : '',
                    })
                  }
                  required={formData.role === 'customer'}
                  disabled={!!preselectedCompanyId}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none disabled:bg-gray-100"
                >
                  <option value="">Select Company</option>
                  {companies.map((company: Company) => (
                    <option key={company.id} value={company.id}>
                      {company.name}
                    </option>
                  ))}
                </select>
              </div>
              {formData.role === 'customer' && (
                <p className="text-xs text-gray-500 mt-1">
                  Customers must be assigned to a company
                </p>
              )}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Message (optional)
            </label>
            <textarea
              value={formData.message}
              onChange={(e) => setFormData({ ...formData, message: e.target.value })}
              placeholder="Add a personal message to include in the invitation email..."
              rows={3}
              maxLength={1000}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            />
            <p className="text-xs text-gray-400 mt-1 text-right">
              {formData.message.length}/1000
            </p>
          </div>

          <div className="bg-blue-50 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              <strong>Note:</strong> The invitation will be valid for 7 days. The user will
              receive an email with a link to create their account.
            </p>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 hover:text-gray-900"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={inviteMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
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
