import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { api } from '@/lib/api'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import {
  Plus,
  User as UserIcon,
  Building2,
  Edit2,
  Trash2,
  X,
  Mail,
  RefreshCw,
  XCircle,
  Clock,
  MessageCircle,
} from 'lucide-react'
import type { User, UserRole, Company, Invitation, InvitationStatus } from '@/types'
import InviteUserDialog from '@/components/InviteUserDialog'
import ConfirmationDialog from '@/components/ConfirmationDialog'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import PageHeader from '@/components/PageHeader'
import { SearchInput } from '@/components/form'
import Skeleton from '@/components/Skeleton'
import { TableSkeleton } from '@/components/skeletons'
import { VirtualizedTable } from '@/components/VirtualizedTable'
import { extractApiErrorMessage, useToast } from '@/lib/toast'
import { userCreateSchema, userUpdateSchema } from '@/lib/validation/schemas'
import { validateForm, type FieldErrors } from '@/lib/validation'

type UserCreateFormData = {
  email: string
  username: string
  full_name: string
  password: string
  role: UserRole
  tenant_id?: number
}

type UserUpdateFormData = {
  email?: string
  full_name?: string
  role?: UserRole
  is_active?: boolean
  tenant_id?: number | null
}

type UserFormSubmission = UserCreateFormData | UserUpdateFormData

export default function UsersPage() {
  const { isAdmin, isManager, user: currentUser } = useAuth()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const toast = useToast()
  
  const [searchInput, setSearchInput] = useState('')
  const debouncedSearch = useDebouncedValue(searchInput, 300)
  const [roleFilter, setRoleFilter] = useState<UserRole | ''>('')
  const [companyFilter, setCompanyFilter] = useState<number | ''>('')
  const [statusFilter, setStatusFilter] = useState<boolean | ''>('')
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showInviteDialog, setShowInviteDialog] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [pendingConfirm, setPendingConfirm] = useState<{ title: string; description: string; onConfirm: () => void } | null>(null)

  const { data: users, isLoading, error } = useQuery({
    queryKey: ['users', roleFilter, companyFilter, statusFilter, debouncedSearch],
    queryFn: () => api.getUsers({
      role: roleFilter || undefined,
      company_id: companyFilter || undefined,
      is_active: statusFilter === '' ? undefined : statusFilter,
      search: debouncedSearch || undefined,
    }),
    enabled: isManager,
  })

  const { data: companiesData } = useQuery({
    queryKey: ['companies'],
    queryFn: () => api.getCompanies(),
    enabled: isManager,
  })

  const companies = companiesData?.items || []

  // Fetch pending invitations
  const { data: invitationsData, isLoading: isInvitationsLoading } = useQuery({
    queryKey: ['invitations', 'pending'],
    queryFn: () => api.getInvitations({ status: 'pending' as InvitationStatus, per_page: 50 }),
    enabled: isManager,
  })

  const pendingInvitations = invitationsData?.items || []

  const createMutation = useMutation({
    mutationFn: (data: UserCreateFormData) => api.createUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setShowCreateDialog(false)
      toast.success('User created')
    },
    onError: (error: unknown) => {
      toast.error('Failed to create user', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: UserUpdateFormData }) =>
      api.updateUser(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setEditingUser(null)
      toast.success('User updated')
    },
    onError: (error: unknown) => {
      toast.error('Failed to update user', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      toast.success('User deactivated')
    },
    onError: (error: unknown) => {
      toast.error('Failed to deactivate user', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  const cancelInvitationMutation = useMutation({
    mutationFn: (id: number) => api.cancelInvitation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations'] })
      toast.success('Invitation cancelled')
    },
    onError: (error: unknown) => {
      toast.error('Failed to cancel invitation', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  const resendInvitationMutation = useMutation({
    mutationFn: (id: number) => api.resendInvitation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations'] })
      toast.success('Invitation resent')
    },
    onError: (error: unknown) => {
      toast.error('Failed to resend invitation', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  // X1-039: Start direct chat with user
  const messageMutation = useMutation({
    mutationFn: (userId: number) => api.createDirectChat({ user_id: userId }),
    onSuccess: (chat) => {
      navigate(`/chat?id=${chat.id}`)
    },
    onError: (error: unknown) => {
      toast.error('Failed to start chat', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  if (!isManager) {
    return (
      <div className="surface-card rounded-2xl bg-amber-50 p-6 text-amber-700 dark:bg-amber-950/30 dark:text-amber-200">
        You don't have permission to view this page.
      </div>
    )
  }

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'system_admin':
        return 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-200'
      case 'admin':
        return 'bg-purple-100 text-purple-700 dark:bg-purple-950/40 dark:text-purple-200'
      case 'manager':
        return 'bg-amber-100 text-amber-700 dark:bg-amber-950/30 dark:text-amber-200'
      case 'editor':
        return 'bg-sky-100 text-sky-700 dark:bg-sky-950/40 dark:text-sky-200'
      case 'customer':
        return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200'
      default:
        return 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
    }
  }

  const roles: UserRole[] = ['system_admin', 'admin', 'manager', 'editor', 'viewer', 'customer']
  const totalUsers = users?.length ?? 0

  return (
    <div className="page-stack">
      <PageHeader
        title="User Management"
        subtitle="Manage users in your organization"
        actions={
          <>
            <button
              type="button"
              onClick={() => setShowInviteDialog(true)}
              className="btn-success table-action-btn"
            >
              <Mail className="w-4 h-4" />
              Invite User
            </button>
            <button
              type="button"
              onClick={() => setShowCreateDialog(true)}
              className="btn-primary table-action-btn"
            >
              <Plus className="w-4 h-4" />
              Add User
            </button>
          </>
        }
      />

      {/* Filters */}
      <div className="admin-sticky-toolbar">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="body-copy inline-flex flex-wrap items-center gap-2">
            <span className="admin-summary-badge">
              {isLoading ? <Skeleton className="h-4 w-20" /> : `${totalUsers} users`}
            </span>
            {pendingInvitations.length > 0 && (
              <span className="pill border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/70 dark:bg-amber-950/30 dark:text-amber-200">
                {pendingInvitations.length} pending invites
              </span>
            )}
          </div>

          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4 xl:items-center">
            <div className="sm:col-span-2 xl:col-span-1 min-w-[220px]">
              <SearchInput
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onClear={() => setSearchInput('')}
                placeholder="Search users..."
                aria-label="Search users by name or email"
              />
            </div>
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value as UserRole | '')}
              className="select-field min-w-[150px]"
            >
              <option value="">All Roles</option>
              {roles.map((role) => (
                <option key={role} value={role}>
                  {role.replace('_', ' ')}
                </option>
              ))}
            </select>

            <select
              value={companyFilter}
              onChange={(e) => setCompanyFilter(e.target.value ? Number(e.target.value) : '')}
              className="select-field min-w-[150px]"
            >
              <option value="">All Companies</option>
              {companies.map((company: Company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </select>

            <select
              value={statusFilter === '' ? '' : statusFilter ? 'active' : 'inactive'}
              onChange={(e) => {
                if (e.target.value === '') setStatusFilter('')
                else setStatusFilter(e.target.value === 'active')
              }}
              className="select-field min-w-[150px]"
            >
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
        </div>
      </div>

      {/* Users table */}
      {isLoading ? (
        <TableSkeleton rows={7} columns={5} />
      ) : error ? (
        <ErrorState
          title="Users could not be loaded"
          message="We could not fetch the current user roster."
          onRetry={() => void queryClient.invalidateQueries({ queryKey: ['users'] })}
        />
      ) : users?.length === 0 ? (
        <EmptyState
          icon={<UserIcon className="h-8 w-8" aria-hidden="true" />}
          title="No users found"
          description="Try adjusting the filters or add a new user to get started."
          action={{ label: 'Add User', onClick: () => setShowCreateDialog(true) }}
        />
      ) : (
        <VirtualizedTable
          items={users ?? []}
          ariaLabel="Users"
          columns={[
            { header: 'User' },
            { header: 'Role' },
            { header: 'Company' },
            { header: 'Status' },
            { header: 'Actions', headerClassName: 'text-right' },
          ]}
          gridTemplateColumns="minmax(18rem, 2fr) minmax(8rem, 0.8fr) minmax(12rem, 1fr) minmax(8rem, 0.8fr) minmax(10rem, 0.9fr)"
          estimateRowHeight={84}
          rowKey={(user) => user.id}
          renderRow={(user: User) => (
            <>
              <div className="admin-table-cell">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-sky-100">
                    <UserIcon className="h-4 w-4 text-sky-600" />
                  </div>
                  <div className="min-w-0">
                    <div className="truncate font-medium text-slate-900 dark:text-slate-100">{user.full_name}</div>
                    <div className="truncate text-xs text-slate-500 dark:text-slate-400">{user.email}</div>
                  </div>
                </div>
              </div>
              <div className="admin-table-cell">
                <span className={`pill capitalize ${getRoleBadgeColor(user.role)}`}>
                  {user.role.replace('_', ' ')}
                </span>
              </div>
              <div className="admin-table-cell">
                {user.company_name ? (
                  <div className="body-copy flex items-center gap-1">
                    <Building2 className="h-3 w-3" />
                    {user.company_name}
                  </div>
                ) : (
                  <span className="text-sm italic text-slate-400">No company</span>
                )}
              </div>
              <div className="admin-table-cell">
                  <span className={`pill ${
                  user.is_active
                    ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200'
                    : 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-200'
                }`}>
                  {user.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <div className="admin-table-cell">
                <div className="flex items-center justify-end gap-1">
                  {user.id !== currentUser?.id && user.role !== 'viewer' ? (
                    <button
                      onClick={() => messageMutation.mutate(user.id)}
                      disabled={messageMutation.isPending}
                      className="admin-icon-action"
                      title="Send message"
                      aria-label={`Send message to ${user.full_name}`}
                    >
                      <MessageCircle className="h-4 w-4" />
                    </button>
                  ) : null}
                  <button
                    onClick={() => setEditingUser(user)}
                    className="admin-icon-action"
                    title="Edit"
                    aria-label={`Edit ${user.full_name}`}
                  >
                    <Edit2 className="h-4 w-4" />
                  </button>
                  {user.id !== currentUser?.id ? (
                    <button
                      onClick={() => {
                        setPendingConfirm({
                          title: 'Deactivate user',
                          description: `Are you sure you want to deactivate ${user.full_name}?`,
                          onConfirm: () => {
                            deleteMutation.mutate(user.id)
                            setPendingConfirm(null)
                          },
                        })
                      }}
                      className="admin-icon-action-danger"
                      title="Deactivate"
                      aria-label={`Deactivate ${user.full_name}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  ) : null}
                </div>
              </div>
            </>
          )}
        />
      )}

      {/* Pending Invitations */}
      <div className="admin-table-shell">
        <div className="border-b border-slate-200 bg-slate-50 px-6 py-4 dark:border-slate-800 dark:bg-slate-950/70">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-amber-600" />
            <h3 className="section-title">Pending Invitations</h3>
            {!isInvitationsLoading && pendingInvitations.length > 0 && (
              <span className="pill bg-amber-100 text-amber-700 dark:bg-amber-950/30 dark:text-amber-200">
                {pendingInvitations.length}
              </span>
            )}
          </div>
        </div>
        {isInvitationsLoading ? (
          <TableSkeleton rows={3} columns={6} />
        ) : pendingInvitations.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon={<Mail className="h-8 w-8" aria-hidden="true" />}
              title="No pending invitations"
              description="New user invitations will appear here until they are accepted or canceled."
              action={{ label: 'Invite User', onClick: () => setShowInviteDialog(true) }}
            />
          </div>
        ) : (
          <div className="admin-table-scroll">
            <table className="admin-table">
              <thead className="admin-table-head">
                <tr>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Company</th>
                  <th>Invited By</th>
                  <th>Expires</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {pendingInvitations.map((invitation: Invitation) => (
                  <tr key={invitation.id} className="admin-table-row">
                    <td className="admin-table-cell">
                      <div className="flex items-center gap-2">
                        <Mail className="w-4 h-4 text-slate-400 dark:text-slate-500" />
                        <span className="text-slate-900 dark:text-slate-100">{invitation.email}</span>
                      </div>
                    </td>
                    <td className="admin-table-cell">
                      <span className={`pill capitalize ${getRoleBadgeColor(invitation.role)}`}>
                        {invitation.role.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="admin-table-cell">
                      {invitation.tenant_name ? (
                        <div className="body-copy flex items-center gap-1">
                          <Building2 className="w-3 h-3" />
                          {invitation.tenant_name}
                        </div>
                      ) : (
                        <span className="text-sm text-slate-400 dark:text-slate-500">-</span>
                      )}
                    </td>
                    <td className="admin-table-cell body-copy">
                      {invitation.inviter_name || '-'}
                    </td>
                    <td className="admin-table-cell">
                      <span className="text-sm text-slate-500 dark:text-slate-400">
                        {new Date(invitation.expires_at).toLocaleDateString()}
                      </span>
                    </td>
                    <td className="admin-table-cell text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => resendInvitationMutation.mutate(invitation.id)}
                          disabled={resendInvitationMutation.isPending}
                          className="admin-icon-action"
                          title="Resend Invitation"
                          aria-label={`Resend invitation to ${invitation.email}`}
                        >
                          <RefreshCw className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => {
                            setPendingConfirm({
                              title: 'Cancel invitation',
                              description: `Are you sure you want to cancel the invitation for ${invitation.email}?`,
                              onConfirm: () => { cancelInvitationMutation.mutate(invitation.id); setPendingConfirm(null) },
                            })
                          }}
                          disabled={cancelInvitationMutation.isPending}
                          className="admin-icon-action-danger"
                          title="Cancel Invitation"
                          aria-label={`Cancel invitation for ${invitation.email}`}
                        >
                          <XCircle className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Confirmation Dialog */}
      <ConfirmationDialog
        open={!!pendingConfirm}
        title={pendingConfirm?.title ?? ''}
        description={pendingConfirm?.description}
        confirmLabel="Confirm"
        onConfirm={() => pendingConfirm?.onConfirm()}
        onCancel={() => setPendingConfirm(null)}
      />

      {/* Create User Dialog */}
      {showCreateDialog && (
        <UserFormDialog
          title="Create User"
          companies={companies}
          currentUserRole={currentUser?.role || 'viewer'}
          onSubmit={(data) => createMutation.mutate(data as UserCreateFormData)}
          onClose={() => setShowCreateDialog(false)}
          isLoading={createMutation.isPending}
        />
      )}

      {/* Edit User Dialog */}
      {editingUser && (
        <UserFormDialog
          title="Edit User"
          user={editingUser}
          companies={companies}
          currentUserRole={currentUser?.role || 'viewer'}
          onSubmit={(data) => updateMutation.mutate({ id: editingUser.id, data: data as UserUpdateFormData })}
          onClose={() => setEditingUser(null)}
          isLoading={updateMutation.isPending}
        />
      )}

      {/* Invite User Dialog */}
      {showInviteDialog && (
        <InviteUserDialog
          currentUserRole={currentUser?.role || 'viewer'}
          currentUserTenantId={currentUser?.tenant_id}
          onClose={() => setShowInviteDialog(false)}
        />
      )}
    </div>
  )
}

interface UserFormDialogProps {
  title: string
  user?: User
  companies: Company[]
  currentUserRole: UserRole
  onSubmit: (data: UserFormSubmission) => void
  onClose: () => void
  isLoading: boolean
}

function UserFormDialog({ title, user, companies, currentUserRole, onSubmit, onClose, isLoading }: UserFormDialogProps) {
  const [formData, setFormData] = useState({
    email: user?.email || '',
    username: user?.username || '',
    full_name: user?.full_name || '',
    password: '',
    role: user?.role || 'viewer' as UserRole,
    tenant_id: user?.tenant_id || '',
    is_active: user?.is_active ?? true,
  })
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})

  const isEdit = !!user
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
    setFieldErrors({})

    if (isEdit) {
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
          formData.tenant_id !== user.tenant_id
            ? formData.tenant_id === ''
              ? null
              : Number(formData.tenant_id)
            : undefined,
      })
    } else {
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
  }

  return (
    <div className="modal-overlay flex items-center justify-center p-4">
      <button type="button" className="absolute inset-0" onClick={onClose} aria-label={`Close ${title} dialog`} />
      <div className="modal-content relative w-full max-w-md">
        <div className="flex items-center justify-between border-b border-slate-200 p-6 dark:border-slate-800">
          <h2 className="text-lg font-display font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-200">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {Object.keys(fieldErrors).length > 0 && (
            <div role="alert" className="p-3 bg-rose-50 text-rose-700 rounded-xl border border-rose-200 text-sm">
              {Object.values(fieldErrors)[0]}
            </div>
          )}
          {!isEdit && (
            <>
              <div>
                <label htmlFor="user-form-username" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">Username</label>
                <input
                  id="user-form-username"
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  required
                  minLength={3}
                  className="input-field"
                />
              </div>
              <div>
                <label htmlFor="user-form-password" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">Password</label>
                <input
                  id="user-form-password"
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required
                  minLength={8}
                  className="input-field"
                />
              </div>
            </>
          )}

          <div>
            <label htmlFor="user-form-email" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">Email</label>
            <input
              id="user-form-email"
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
              className="input-field"
            />
          </div>

          <div>
            <label htmlFor="user-form-full-name" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">Full Name</label>
            <input
              id="user-form-full-name"
              type="text"
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              required
              className="input-field"
            />
          </div>

          <div>
            <label htmlFor="user-form-role" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">Role</label>
            <select
              id="user-form-role"
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value as UserRole })}
              className="select-field"
            >
              {availableRoles.map((role) => (
                <option key={role} value={role}>
                  {role.replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>

          {/* Show company selector for customer role or if editing a customer */}
          {(formData.role === 'customer' || user?.role === 'customer') && (
            <div>
              <label htmlFor="user-form-company" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">
                Company <span className="text-rose-500">*</span>
              </label>
              <select
                id="user-form-company"
                value={formData.tenant_id}
                onChange={(e) => setFormData({ ...formData, tenant_id: e.target.value ? Number(e.target.value) : '' })}
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
              {formData.role === 'customer' && (
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Customers must be assigned to a company</p>
              )}
            </div>
          )}

          {isEdit && (
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_active"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="rounded border-slate-300"
              />
              <label htmlFor="is_active" className="text-sm text-slate-700 dark:text-slate-200">Active</label>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary"
            >
              {isLoading ? 'Saving...' : isEdit ? 'Save Changes' : 'Create User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
