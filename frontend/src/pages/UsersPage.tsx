import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/lib/auth'
import { api } from '@/lib/api'
import {
  Search,
  Filter,
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
} from 'lucide-react'
import type { User, UserRole, Company, Invitation, InvitationStatus } from '@/types'
import InviteUserDialog from '@/components/InviteUserDialog'

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
  const { isAdmin, user: currentUser } = useAuth()
  const queryClient = useQueryClient()
  
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<UserRole | ''>('')
  const [companyFilter, setCompanyFilter] = useState<number | ''>('')
  const [statusFilter, setStatusFilter] = useState<boolean | ''>('')
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showInviteDialog, setShowInviteDialog] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)

  const { data: users, isLoading, error } = useQuery({
    queryKey: ['users', roleFilter, companyFilter, statusFilter, search],
    queryFn: () => api.getUsers({
      role: roleFilter || undefined,
      company_id: companyFilter || undefined,
      is_active: statusFilter === '' ? undefined : statusFilter,
      search: search || undefined,
    }),
    enabled: isAdmin,
  })

  const { data: companiesData } = useQuery({
    queryKey: ['companies'],
    queryFn: () => api.getCompanies(),
    enabled: isAdmin,
  })

  const companies = companiesData?.items || []

  // Fetch pending invitations
  const { data: invitationsData } = useQuery({
    queryKey: ['invitations', 'pending'],
    queryFn: () => api.getInvitations({ status: 'pending' as InvitationStatus, per_page: 50 }),
    enabled: isAdmin,
  })

  const pendingInvitations = invitationsData?.items || []

  const createMutation = useMutation({
    mutationFn: (data: UserCreateFormData) => api.createUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setShowCreateDialog(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: UserUpdateFormData }) =>
      api.updateUser(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setEditingUser(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })

  const cancelInvitationMutation = useMutation({
    mutationFn: (id: number) => api.cancelInvitation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations'] })
    },
  })

  const resendInvitationMutation = useMutation({
    mutationFn: (id: number) => api.resendInvitation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations'] })
    },
  })

  if (!isAdmin) {
    return (
      <div className="surface-card rounded-2xl p-6 text-amber-700 bg-amber-50">
        You don't have permission to view this page.
      </div>
    )
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

  const roles: UserRole[] = ['system_admin', 'admin', 'manager', 'editor', 'viewer', 'customer']

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-slate-900">User Management</h1>
          <p className="text-slate-500 mt-1">Manage users in your organization</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowInviteDialog(true)}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-xl hover:bg-emerald-700"
          >
            <Mail className="w-4 h-4" />
            Invite User
          </button>
          <button
            onClick={() => setShowCreateDialog(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add User
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="surface-card rounded-2xl p-4">
        <div className="flex items-center gap-4 flex-wrap">
          {/* Search */}
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search users..."
                className="input-field pl-10"
              />
            </div>
          </div>

          {/* Role Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value as UserRole | '')}
              className="select-field"
            >
              <option value="">All Roles</option>
              {roles.map((role) => (
                <option key={role} value={role}>
                  {role.replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>

          {/* Company Filter */}
          <select
            value={companyFilter}
            onChange={(e) => setCompanyFilter(e.target.value ? Number(e.target.value) : '')}
            className="select-field"
          >
            <option value="">All Companies</option>
            {companies.map((company: Company) => (
              <option key={company.id} value={company.id}>
                {company.name}
              </option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter === '' ? '' : statusFilter ? 'active' : 'inactive'}
            onChange={(e) => {
              if (e.target.value === '') setStatusFilter('')
              else setStatusFilter(e.target.value === 'active')
            }}
            className="select-field"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
      </div>

      {/* Users table */}
      <div className="surface-card rounded-2xl overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">User</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Role</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Company</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Status</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {isLoading ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-slate-500">
                  Loading users...
                </td>
              </tr>
            ) : error ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-rose-500">
                  Failed to load users
                </td>
              </tr>
            ) : users?.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-slate-500">
                  No users found
                </td>
              </tr>
            ) : (
              users?.map((user: User) => (
                <tr key={user.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-sky-100 rounded-full flex items-center justify-center">
                        <UserIcon className="w-4 h-4 text-sky-600" />
                      </div>
                      <div>
                        <div className="font-medium text-slate-900">{user.full_name}</div>
                        <div className="text-sm text-slate-500">{user.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`pill capitalize ${getRoleBadgeColor(user.role)}`}>
                      {user.role.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    {user.company_name ? (
                      <div className="flex items-center gap-1 text-sm text-slate-600">
                        <Building2 className="w-3 h-3" />
                        {user.company_name}
                      </div>
                    ) : (
                      <span className="text-slate-400 text-sm">-</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`pill ${
                      user.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
                    }`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => setEditingUser(user)}
                        className="p-1 text-slate-500 hover:text-sky-600"
                        title="Edit"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      {user.id !== currentUser?.id && (
                        <button
                          onClick={() => {
                            if (confirm(`Deactivate user ${user.full_name}?`)) {
                              deleteMutation.mutate(user.id)
                            }
                          }}
                          className="p-1 text-slate-500 hover:text-rose-600"
                          title="Deactivate"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pending Invitations */}
      {pendingInvitations.length > 0 && (
        <div className="surface-card rounded-2xl overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-amber-600" />
              <h3 className="font-display font-semibold text-slate-900">Pending Invitations</h3>
              <span className="pill bg-amber-100 text-amber-700">
                {pendingInvitations.length}
              </span>
            </div>
          </div>
          <table className="w-full">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Email</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Role</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Company</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Invited By</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Expires</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {pendingInvitations.map((invitation: Invitation) => (
                <tr key={invitation.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <Mail className="w-4 h-4 text-slate-400" />
                      <span className="text-slate-900">{invitation.email}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`pill capitalize ${getRoleBadgeColor(invitation.role)}`}>
                      {invitation.role.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    {invitation.tenant_name ? (
                      <div className="flex items-center gap-1 text-sm text-slate-600">
                        <Building2 className="w-3 h-3" />
                        {invitation.tenant_name}
                      </div>
                    ) : (
                      <span className="text-slate-400 text-sm">-</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600">
                    {invitation.inviter_name || '-'}
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-slate-500">
                      {new Date(invitation.expires_at).toLocaleDateString()}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => resendInvitationMutation.mutate(invitation.id)}
                        disabled={resendInvitationMutation.isPending}
                        className="p-1 text-slate-500 hover:text-sky-600"
                        title="Resend Invitation"
                      >
                        <RefreshCw className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => {
                          if (confirm(`Cancel invitation for ${invitation.email}?`)) {
                            cancelInvitationMutation.mutate(invitation.id)
                          }
                        }}
                        disabled={cancelInvitationMutation.isPending}
                        className="p-1 text-slate-500 hover:text-rose-600"
                        title="Cancel Invitation"
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
    if (isEdit) {
      onSubmit({
        email: formData.email !== user.email ? formData.email : undefined,
        full_name: formData.full_name !== user.full_name ? formData.full_name : undefined,
        role: formData.role !== user.role ? formData.role : undefined,
        is_active: formData.is_active !== user.is_active ? formData.is_active : undefined,
        tenant_id:
          formData.tenant_id !== user.tenant_id
            ? formData.tenant_id === ''
              ? null
              : Number(formData.tenant_id)
            : undefined,
      })
    } else {
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
    <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between p-6 border-b border-slate-200">
          <h2 className="text-lg font-display font-semibold text-slate-900">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {!isEdit && (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Username</label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  required
                  minLength={3}
                  className="input-field"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
                <input
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
            <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
              className="input-field"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Full Name</label>
            <input
              type="text"
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              required
              className="input-field"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Role</label>
            <select
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
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Company <span className="text-rose-500">*</span>
              </label>
              <select
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
                <p className="text-xs text-slate-500 mt-1">Customers must be assigned to a company</p>
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
              <label htmlFor="is_active" className="text-sm text-slate-700">Active</label>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-slate-700 hover:text-slate-900"
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
