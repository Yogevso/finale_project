import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/lib/auth'
import { api } from '@/lib/api'
import { extractApiErrorMessage, useToast } from '@/lib/toast'
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
import ConfirmationDialog from '@/components/ConfirmationDialog'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { FormField, SubmitButton } from '@/components/form'
import PageHeader from '@/components/PageHeader'
import { StatCardSkeleton } from '@/components/skeletons'

export default function CompanyDetailPage() {
  const { id } = useParams<{ id: string }>()
  const companyId = parseInt(id || '0')
  const { isAdmin } = useAuth()
  const queryClient = useQueryClient()
  const toast = useToast()
  const [showEditForm, setShowEditForm] = useState(false)
  const [showAddUser, setShowAddUser] = useState(false)
  const [userEmail, setUserEmail] = useState('')
  const [userEmailError, setUserEmailError] = useState('')
  const [activeTab, setActiveTab] = useState<'users' | 'documents'>('users')
  const [docPage, setDocPage] = useState(1)
  const [userToRemove, setUserToRemove] = useState<CompanyUser | null>(null)

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
      toast.success('User added to company')
    },
    onError: (error: unknown) => {
      toast.error('Failed to add user', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  const removeUserMutation = useMutation({
    mutationFn: (userId: number) => api.removeUserFromCompany(companyId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company', companyId] })
      toast.success('User removed from company')
    },
    onError: (error: unknown) => {
      toast.error('Failed to remove user', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  const handleAddUser = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmedEmail = userEmail.trim()
    setUserEmailError('')

    if (!trimmedEmail) {
      setUserEmailError('Email is required.')
      return
    }

    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailPattern.test(trimmedEmail)) {
      setUserEmailError('Enter a valid email address.')
      return
    }

    addUserMutation.mutate(trimmedEmail)
  }

  const handleRemoveUser = (user: CompanyUser) => {
    setUserToRemove(user)
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
      <div className="surface-card animate-fade-in rounded-2xl p-6 text-amber-700 bg-amber-50">
        You don't have permission to view this page.
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="page-stack">
        <StatCardSkeleton count={5} />
      </div>
    )
  }

  if (error || !company) {
    return (
      <div className="animate-fade-in">
        <ErrorState
          title="Company details unavailable"
          message="Company not found or failed to load."
        />
      </div>
    )
  }

  return (
    <div className="page-stack">
      <PageHeader
        title={company.name}
        subtitle={company.slug}
        actions={
          <>
            <Link to="/admin/companies" className="btn-ghost table-action-btn inline-flex items-center gap-2">
              <ArrowLeft className="w-4 h-4" />
              Back
            </Link>
            <button
              onClick={() => setShowEditForm(true)}
              className="btn-primary table-action-btn flex items-center gap-2"
            >
              <Edit className="w-4 h-4" />
              Edit
            </button>
          </>
        }
      />

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="surface-card rounded-2xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-sky-100 rounded-xl flex items-center justify-center">
              <Building2 className="w-5 h-5 text-sky-600" />
            </div>
            <div>
              <p className="metric-label">Type</p>
              <p className="metric-value text-base capitalize">{company.company_type}</p>
            </div>
          </div>
        </div>
        <div className="surface-card rounded-2xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-100 rounded-xl flex items-center justify-center">
              <Users className="w-5 h-5 text-emerald-600" />
            </div>
            <div>
              <p className="metric-label">Users</p>
              <p className="metric-value text-base">{company.user_count}</p>
            </div>
          </div>
        </div>
        <div className="surface-card rounded-2xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-xl flex items-center justify-center">
              <FileText className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="metric-label">Assigned Docs</p>
              <p className="metric-value text-base">{company.assigned_document_count}</p>
            </div>
          </div>
        </div>
        <div className="surface-card rounded-2xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center">
              <FileText className="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <p className="metric-label">Customer Visible</p>
              <p className="metric-value text-base">{company.customer_visible_document_count}</p>
            </div>
          </div>
        </div>
        <div className="surface-card rounded-2xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-amber-100 rounded-xl flex items-center justify-center">
              <Mail className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <p className="metric-label">Contact</p>
              <p className="metric-value truncate text-base">{company.contact_email || 'N/A'}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Company Info */}
      <div className="surface-card rounded-2xl p-6">
        <h2 className="section-title mb-4">Company Information</h2>
        <dl className="grid grid-cols-2 gap-4">
          <div>
            <dt className="helper-copy">Status</dt>
            <dd>
              <span className={`pill ${
                company.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
              }`}>
                {company.is_active ? 'Active' : 'Inactive'}
              </span>
            </dd>
          </div>
          <div>
            <dt className="helper-copy">Created</dt>
            <dd className="body-copy flex items-center gap-2 text-slate-900 dark:text-slate-100">
              <Calendar className="w-4 h-4 text-slate-400" />
              {new Date(company.created_at).toLocaleDateString()}
            </dd>
          </div>
          {company.company_logo && (
            <div className="col-span-2">
              <dt className="helper-copy mb-2">Logo</dt>
              <dd>
                <img
                  src={company.company_logo}
                  alt="Company logo"
                  className="h-12 w-auto object-contain"
                  decoding="async"
                  height={48}
                  loading="lazy"
                  width={160}
                />
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
            type="button"
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
            type="button"
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
            <h3 className="section-title">Company Users</h3>
            <button
              onClick={() => setShowAddUser(true)}
              className="btn-primary table-action-btn flex items-center gap-2"
            >
              <UserPlus className="w-4 h-4" />
              Add User
            </button>
          </div>

          {showAddUser && (
            <div className="p-4 bg-slate-50 border-b border-slate-200">
              <form onSubmit={handleAddUser} className="flex flex-col gap-3 md:flex-row md:items-end">
                <FormField label="User email" htmlFor="company-user-email" error={userEmailError} required className="flex-1">
                  <input
                    id="company-user-email"
                    type="email"
                    value={userEmail}
                    onChange={(e) => setUserEmail(e.target.value)}
                    placeholder="Enter user email"
                    required
                    aria-invalid={!!userEmailError || !!addUserMutation.error || undefined}
                    className="input-field flex-1"
                  />
                </FormField>
                <SubmitButton
                  type="submit"
                  disabled={addUserMutation.isPending}
                  isLoading={addUserMutation.isPending}
                  loadingText="Adding..."
                >
                  Add user
                </SubmitButton>
                <button
                  type="button"
                  onClick={() => { setShowAddUser(false); setUserEmail('') }}
                  className="btn-ghost table-action-btn"
                >
                  Cancel
                </button>
              </form>
              {addUserMutation.error ? (
                <p className="mt-2 text-sm text-rose-600">
                  {extractApiErrorMessage(addUserMutation.error, 'Failed to add user')}
                </p>
              ) : null}
            </div>
          )}

          {!company.users || company.users.length === 0 ? (
            <div className="p-6">
              <EmptyState
                title="No users in this company"
                description="Add the first user to start assigning access for this account."
                action={{
                  label: 'Add user',
                  onClick: () => setShowAddUser(true),
                }}
              />
            </div>
          ) : (
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
                {company.users.map((user) => (
                  <tr key={user.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4">
                      <div className="card-title">{user.full_name || 'N/A'}</div>
                      <div className="body-copy">{user.email}</div>
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
                        className="btn-icon h-9 w-9 text-rose-600 hover:bg-rose-50 hover:text-rose-700"
                        title="Remove from company"
                        aria-label={`Remove ${user.full_name || user.email} from company`}
                        type="button"
                      >
                        <UserMinus className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Documents Tab */}
      {activeTab === 'documents' && (
        <div className="surface-card rounded-2xl overflow-hidden">
          {!documents?.items || documents.items.length === 0 ? (
            <div className="p-6">
              <EmptyState
                title="No documents assigned"
                description="This company does not have any assigned documents yet."
              />
            </div>
          ) : (
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
                {documents.items.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4">
                      <div className="card-title">{doc.title}</div>
                    </td>
                    <td className="px-6 py-4 body-copy">
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
                    <td className="px-6 py-4 helper-copy">
                      {new Date(doc.updated_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        to={`/documents/${doc.id}/fullscreen`}
                        className="btn-secondary table-action-btn inline-flex"
                        aria-label={`Open ${doc.title}`}
                      >
                        <ChevronRight className="w-4 h-4" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {documents && documents.total_pages > 1 && (
            <div className="flex justify-center gap-2 p-4 border-t border-slate-200">
              <button
                onClick={() => setDocPage(p => Math.max(1, p - 1))}
                disabled={docPage === 1}
                className="btn-ghost table-action-btn disabled:opacity-50"
                type="button"
              >
                Previous
              </button>
              <span className="body-copy px-4 py-2">
                Page {docPage} of {documents.total_pages}
              </span>
              <button
                onClick={() => setDocPage(p => Math.min(documents.total_pages, p + 1))}
                disabled={docPage === documents.total_pages}
                className="btn-ghost table-action-btn disabled:opacity-50"
                type="button"
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

      {/* Remove user confirmation */}
      <ConfirmationDialog
        open={!!userToRemove}
        title="Remove user"
        description={`Are you sure you want to remove ${userToRemove?.full_name || userToRemove?.email} from this company?`}
        confirmLabel="Remove"
        isLoading={removeUserMutation.isPending}
        onConfirm={() => {
          if (userToRemove) {
            removeUserMutation.mutate(userToRemove.id, { onSettled: () => setUserToRemove(null) })
          }
        }}
        onCancel={() => setUserToRemove(null)}
      />
    </div>
  )
}
