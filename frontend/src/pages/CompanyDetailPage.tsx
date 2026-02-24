import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/lib/auth'
import { api } from '@/lib/api'
import { 
  Building2, 
  ArrowLeft, 
  Users, 
  FileText, 
  Mail, 
  Calendar, 
  Edit, 
  UserPlus, 
  UserMinus,
  ChevronRight 
} from 'lucide-react'
import type { CompanyUser } from '@/types'
import CompanyForm from '@/components/CompanyForm'

export default function CompanyDetailPage() {
  const { id } = useParams<{ id: string }>()
  const companyId = parseInt(id || '0')
  const { isAdmin } = useAuth()
  const queryClient = useQueryClient()
  const [showEditForm, setShowEditForm] = useState(false)
  const [showAddUser, setShowAddUser] = useState(false)
  const [userEmail, setUserEmail] = useState('')
  const [activeTab, setActiveTab] = useState<'users' | 'documents'>('users')
  const [docPage, setDocPage] = useState(1)

  const { data: company, isLoading, error } = useQuery({
    queryKey: ['company', companyId],
    queryFn: () => api.getCompany(companyId),
    enabled: isAdmin && !!companyId,
  })

  const { data: documents } = useQuery({
    queryKey: ['company-documents', companyId, docPage],
    queryFn: () =>
      api.getCompanyDocuments(companyId, { page: docPage, per_page: 10, scope: 'assigned' }),
    enabled: isAdmin && !!companyId && activeTab === 'documents',
  })

  const addUserMutation = useMutation({
    mutationFn: (email: string) => api.addUserToCompany(companyId, { email }),
    onSuccess: () => {
      setShowAddUser(false)
      setUserEmail('')
      queryClient.invalidateQueries({ queryKey: ['company', companyId] })
    },
  })

  const removeUserMutation = useMutation({
    mutationFn: (userId: number) => api.removeUserFromCompany(companyId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company', companyId] })
    },
  })

  const handleAddUser = (e: React.FormEvent) => {
    e.preventDefault()
    if (userEmail.trim()) {
      addUserMutation.mutate(userEmail.trim())
    }
  }

  const handleRemoveUser = (user: CompanyUser) => {
    if (confirm(`Are you sure you want to remove ${user.full_name || user.email} from this company?`)) {
      removeUserMutation.mutate(user.id)
    }
  }

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'system_admin':
        return 'bg-rose-100 text-rose-700'
      case 'admin':
        return 'bg-purple-100 text-purple-700'
      case 'manager':
        return 'bg-amber-100 text-amber-700'
      case 'editor':
        return 'bg-sky-100 text-sky-700'
      case 'customer':
        return 'bg-emerald-100 text-emerald-700'
      default:
        return 'bg-slate-100 text-slate-700'
    }
  }

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-emerald-100 text-emerald-700'
      case 'approved':
        return 'bg-sky-100 text-sky-700'
      case 'draft':
        return 'bg-slate-100 text-slate-700'
      case 'pending_review':
        return 'bg-amber-100 text-amber-700'
      case 'archived':
        return 'bg-rose-100 text-rose-700'
      default:
        return 'bg-slate-100 text-slate-700'
    }
  }

  if (!isAdmin) {
    return (
      <div className="surface-card rounded-2xl p-6 text-amber-700 bg-amber-50">
        You don't have permission to view this page.
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-600"></div>
      </div>
    )
  }

  if (error || !company) {
    return (
      <div className="surface-card rounded-2xl p-6 text-rose-700 bg-rose-50">
        Company not found or failed to load.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          to="/admin/companies"
          className="p-2 hover:bg-slate-100 rounded-xl"
        >
          <ArrowLeft className="w-5 h-5 text-slate-600" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-display font-bold text-slate-900">{company.name}</h1>
          <p className="text-slate-500">{company.slug}</p>
        </div>
        <button
          onClick={() => setShowEditForm(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Edit className="w-4 h-4" />
          Edit
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="surface-card rounded-2xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-sky-100 rounded-xl flex items-center justify-center">
              <Building2 className="w-5 h-5 text-sky-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Type</p>
              <p className="font-semibold text-slate-900 capitalize">{company.company_type}</p>
            </div>
          </div>
        </div>
        <div className="surface-card rounded-2xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-100 rounded-xl flex items-center justify-center">
              <Users className="w-5 h-5 text-emerald-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Users</p>
              <p className="font-semibold text-slate-900">{company.user_count}</p>
            </div>
          </div>
        </div>
        <div className="surface-card rounded-2xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-xl flex items-center justify-center">
              <FileText className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Assigned Docs</p>
              <p className="font-semibold text-slate-900">{company.assigned_document_count}</p>
            </div>
          </div>
        </div>
        <div className="surface-card rounded-2xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center">
              <FileText className="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Customer Visible</p>
              <p className="font-semibold text-slate-900">{company.customer_visible_document_count}</p>
            </div>
          </div>
        </div>
        <div className="surface-card rounded-2xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-amber-100 rounded-xl flex items-center justify-center">
              <Mail className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Contact</p>
              <p className="font-semibold text-slate-900 truncate">{company.contact_email || 'N/A'}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Company Info */}
      <div className="surface-card rounded-2xl p-6">
        <h2 className="text-lg font-display font-semibold text-slate-900 mb-4">Company Information</h2>
        <dl className="grid grid-cols-2 gap-4">
          <div>
            <dt className="text-sm text-slate-500">Status</dt>
            <dd>
              <span className={`pill ${
                company.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
              }`}>
                {company.is_active ? 'Active' : 'Inactive'}
              </span>
            </dd>
          </div>
          <div>
            <dt className="text-sm text-slate-500">Created</dt>
            <dd className="flex items-center gap-2 text-slate-900">
              <Calendar className="w-4 h-4 text-slate-400" />
              {new Date(company.created_at).toLocaleDateString()}
            </dd>
          </div>
          {company.company_logo && (
            <div className="col-span-2">
              <dt className="text-sm text-slate-500 mb-2">Logo</dt>
              <dd>
                <img src={company.company_logo} alt="Company logo" className="h-12" />
              </dd>
            </div>
          )}
        </dl>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex gap-8">
          <button
            onClick={() => setActiveTab('users')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'users'
                ? 'border-sky-600 text-sky-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            Users ({company.user_count})
          </button>
          <button
            onClick={() => setActiveTab('documents')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'documents'
                ? 'border-sky-600 text-sky-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            Assigned Documents ({company.assigned_document_count})
          </button>
        </nav>
      </div>

      {/* Users Tab */}
      {activeTab === 'users' && (
        <div className="surface-card rounded-2xl overflow-hidden">
          <div className="flex items-center justify-between p-4 border-b border-slate-200">
            <h3 className="font-display font-semibold text-slate-900">Company Users</h3>
            <button
              onClick={() => setShowAddUser(true)}
              className="btn-primary text-sm px-3 py-1.5 flex items-center gap-2"
            >
              <UserPlus className="w-4 h-4" />
              Add User
            </button>
          </div>

          {showAddUser && (
            <div className="p-4 bg-slate-50 border-b border-slate-200">
              <form onSubmit={handleAddUser} className="flex gap-2">
                <input
                  type="email"
                  value={userEmail}
                  onChange={(e) => setUserEmail(e.target.value)}
                  placeholder="Enter user email"
                  className="input-field flex-1"
                />
                <button
                  type="submit"
                  disabled={addUserMutation.isPending}
                  className="btn-primary disabled:opacity-50"
                >
                  {addUserMutation.isPending ? 'Adding...' : 'Add'}
                </button>
                <button
                  type="button"
                  onClick={() => { setShowAddUser(false); setUserEmail('') }}
                  className="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-xl"
                >
                  Cancel
                </button>
              </form>
              {addUserMutation.error && (
                <p className="mt-2 text-sm text-rose-600">
                  {(addUserMutation.error as Error & { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to add user'}
                </p>
              )}
            </div>
          )}

          <table className="w-full">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">User</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Role</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Status</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {!company.users || company.users.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-slate-500">
                    No users in this company
                  </td>
                </tr>
              ) : (
                company.users.map((user) => (
                  <tr key={user.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4">
                      <div className="font-medium text-slate-900">{user.full_name || 'N/A'}</div>
                      <div className="text-sm text-slate-500">{user.email}</div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`pill capitalize ${getRoleBadgeColor(user.role)}`}>
                        {user.role}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`pill ${
                        user.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
                      }`}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => handleRemoveUser(user)}
                        className="p-2 text-rose-600 hover:bg-rose-50 rounded-xl"
                        title="Remove from company"
                      >
                        <UserMinus className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Documents Tab */}
      {activeTab === 'documents' && (
        <div className="surface-card rounded-2xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Document</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Category</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Updated</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {!documents?.items || documents.items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-slate-500">
                    No documents assigned to this company
                  </td>
                </tr>
              ) : (
                documents.items.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4">
                      <div className="font-medium text-slate-900">{doc.title}</div>
                    </td>
                    <td className="px-6 py-4 text-slate-600">
                      {doc.category || 'Uncategorized'}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`pill capitalize ${getStatusBadgeColor(doc.status)}`}>
                        {doc.status === 'active'
                          ? 'Published'
                          : doc.status === 'approved'
                          ? 'Approved'
                          : doc.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-500 text-sm">
                      {new Date(doc.updated_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        to={`/documents/${doc.id}/fullscreen`}
                        className="p-2 text-slate-600 hover:bg-slate-100 rounded-xl inline-flex"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {documents && documents.pages > 1 && (
            <div className="flex justify-center gap-2 p-4 border-t border-slate-200">
              <button
                onClick={() => setDocPage(p => Math.max(1, p - 1))}
                disabled={docPage === 1}
                className="btn-ghost disabled:opacity-50"
              >
                Previous
              </button>
              <span className="px-4 py-2 text-slate-600">
                Page {docPage} of {documents.pages}
              </span>
              <button
                onClick={() => setDocPage(p => Math.min(documents.pages, p + 1))}
                disabled={docPage === documents.pages}
                className="btn-ghost disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}

      {/* Edit Modal */}
      {showEditForm && (
        <CompanyForm
          company={company}
          onClose={() => setShowEditForm(false)}
          onSuccess={() => {
            setShowEditForm(false)
            queryClient.invalidateQueries({ queryKey: ['company', companyId] })
          }}
        />
      )}
    </div>
  )
}
