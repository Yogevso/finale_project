import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { useAuth } from '@/lib/auth'
import { api } from '@/lib/api'
import { extractApiErrorMessage, useToast } from '@/lib/toast'
import type { Invitation, InvitationStatus, User, UserRole } from '@/types'

import { ALL_USER_ROLES } from '../constants'
import type {
  PendingConfirmState,
  UserCreateFormData,
  UserUpdateFormData,
} from '../types'

export function useUsersPageController() {
  const { isAdmin, isManager, isSystemAdmin, user: currentUser } = useAuth()
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
  const [previewInvitation, setPreviewInvitation] = useState<Invitation | null>(null)
  const [pendingConfirm, setPendingConfirm] = useState<PendingConfirmState>(null)

  const usersQuery = useQuery({
    queryKey: ['users', roleFilter, companyFilter, statusFilter, debouncedSearch],
    queryFn: () =>
      api.getUsers({
        role: roleFilter || undefined,
        company_id: companyFilter || undefined,
        is_active: statusFilter === '' ? undefined : statusFilter,
        search: debouncedSearch || undefined,
      }),
    enabled: isManager,
  })

  const companiesQuery = useQuery({
    queryKey: ['companies'],
    queryFn: () => api.getCompanies(),
    enabled: isManager,
  })

  const invitationsQuery = useQuery({
    queryKey: ['invitations', 'pending'],
    queryFn: () => api.getInvitations({ status: 'pending' as InvitationStatus, per_page: 50 }),
    enabled: isManager,
  })

  const invitationPreviewQuery = useQuery({
    queryKey: ['invitations', 'preview', previewInvitation?.id],
    queryFn: () => api.getInvitationEmailPreview(previewInvitation!.id),
    enabled: isManager && previewInvitation !== null,
  })

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

  const hardDeleteMutation = useMutation({
    mutationFn: (id: number) => api.hardDeleteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      toast.success('User permanently deleted')
    },
    onError: (error: unknown) => {
      toast.error(
        'Failed to permanently delete user',
        extractApiErrorMessage(error, 'Please try again.'),
      )
    },
  })

  const cancelInvitationMutation = useMutation({
    mutationFn: (id: number) => api.cancelInvitation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations'] })
      toast.success('Invitation cancelled')
    },
    onError: (error: unknown) => {
      toast.error(
        'Failed to cancel invitation',
        extractApiErrorMessage(error, 'Please try again.'),
      )
    },
  })

  const resendInvitationMutation = useMutation({
    mutationFn: (id: number) => api.resendInvitation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations'] })
      toast.success('Invitation resent')
    },
    onError: (error: unknown) => {
      toast.error(
        'Failed to resend invitation',
        extractApiErrorMessage(error, 'Please try again.'),
      )
    },
  })

  const messageMutation = useMutation({
    mutationFn: (userId: number) => api.createDirectChat({ user_id: userId }),
    onSuccess: (chat) => {
      navigate(`/chat?id=${chat.id}`)
    },
    onError: (error: unknown) => {
      toast.error('Failed to start chat', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  const users = usersQuery.data ?? []
  const companies = companiesQuery.data?.items ?? []
  const pendingInvitations = invitationsQuery.data?.items ?? []
  const canDeactivateUsers = isAdmin
  const canHardDeleteUsers = isSystemAdmin

  const requestDeactivateUser = (user: User) => {
    setPendingConfirm({
      title: 'Deactivate user',
      description: `${user.full_name} will lose access immediately, but their account can still be restored later.`,
      confirmLabel: 'Deactivate',
      variant: 'warning',
      onConfirm: () => {
        deleteMutation.mutate(user.id)
        setPendingConfirm(null)
      },
    })
  }

  const requestHardDeleteUser = (user: User) => {
    setPendingConfirm({
      title: 'Permanently delete user',
      description: `${user.full_name} will be removed permanently. This only works for inactive users without retained ownership records.`,
      confirmLabel: 'Delete Permanently',
      variant: 'danger',
      onConfirm: () => {
        hardDeleteMutation.mutate(user.id)
        setPendingConfirm(null)
      },
    })
  }

  const requestCancelInvitation = (invitation: Invitation) => {
    setPendingConfirm({
      title: 'Cancel invitation',
      description: `Are you sure you want to cancel the invitation for ${invitation.email}?`,
      onConfirm: () => {
        cancelInvitationMutation.mutate(invitation.id)
        setPendingConfirm(null)
      },
    })
  }

  return {
    isManager,
    isAdmin,
    isSystemAdmin,
    currentUser,
    canDeactivateUsers,
    canHardDeleteUsers,
    roles: ALL_USER_ROLES,
    searchInput,
    setSearchInput,
    roleFilter,
    setRoleFilter,
    companyFilter,
    setCompanyFilter,
    statusFilter,
    setStatusFilter,
    showCreateDialog,
    setShowCreateDialog,
    showInviteDialog,
    setShowInviteDialog,
    editingUser,
    setEditingUser,
    previewInvitation,
    setPreviewInvitation,
    pendingConfirm,
    setPendingConfirm,
    usersQuery,
    users,
    totalUsers: users.length,
    companies,
    pendingInvitations,
    invitationsQuery,
    invitationPreviewQuery,
    createMutation,
    updateMutation,
    deleteMutation,
    hardDeleteMutation,
    cancelInvitationMutation,
    resendInvitationMutation,
    messageMutation,
    requestDeactivateUser,
    requestHardDeleteUser,
    requestCancelInvitation,
  }
}
