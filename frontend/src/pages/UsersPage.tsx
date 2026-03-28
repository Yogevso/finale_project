import { Mail, Plus } from 'lucide-react'

import ConfirmationDialog from '@/components/ConfirmationDialog'
import InviteUserDialog from '@/components/InviteUserDialog'
import PageHeader from '@/components/PageHeader'
import {
  InvitationEmailPreviewDialog,
  PendingInvitationsSection,
  UserFormDialog,
  UsersFiltersToolbar,
  UsersTableSection,
} from '@/pages/users/components'
import { useUsersPageController } from '@/pages/users/hooks'
import type { UserCreateFormData, UserUpdateFormData } from '@/pages/users/types'

export default function UsersPage() {
  const controller = useUsersPageController()
  const currentUser = controller.currentUser
  const editingUser = controller.editingUser

  if (!controller.isManager) {
    return (
      <div className="surface-card rounded-2xl bg-amber-50 p-6 text-amber-700 dark:bg-amber-950/30 dark:text-amber-200">
        You don't have permission to view this page.
      </div>
    )
  }

  return (
    <div className="page-stack">
      <PageHeader
        title="User Management"
        subtitle="Manage users in your organization"
        actions={
          <>
            <button
              type="button"
              onClick={() => controller.setShowInviteDialog(true)}
              className="btn-success table-action-btn"
            >
              <Mail className="h-4 w-4" />
              Invite User
            </button>
            <button
              type="button"
              onClick={() => controller.setShowCreateDialog(true)}
              className="btn-primary table-action-btn"
            >
              <Plus className="h-4 w-4" />
              Add User
            </button>
          </>
        }
      />

      <UsersFiltersToolbar
        isLoading={controller.usersQuery.isLoading}
        totalUsers={controller.totalUsers}
        pendingInvitationCount={controller.pendingInvitations.length}
        searchInput={controller.searchInput}
        onSearchInputChange={controller.setSearchInput}
        onSearchClear={() => controller.setSearchInput('')}
        roleFilter={controller.roleFilter}
        onRoleFilterChange={controller.setRoleFilter}
        companyFilter={controller.companyFilter}
        onCompanyFilterChange={controller.setCompanyFilter}
        statusFilter={controller.statusFilter}
        onStatusFilterChange={controller.setStatusFilter}
        roles={controller.roles}
        companies={controller.companies}
      />

      <UsersTableSection
        users={controller.users}
        isLoading={controller.usersQuery.isLoading}
        isError={controller.usersQuery.isError}
        onRetry={() => void controller.usersQuery.refetch()}
        onOpenCreateDialog={() => controller.setShowCreateDialog(true)}
        onEditUser={controller.setEditingUser}
        onRequestDeactivate={controller.requestDeactivateUser}
        onRequestHardDelete={controller.requestHardDeleteUser}
        onStartDirectChat={(userId) => controller.messageMutation.mutate(userId)}
        currentUserId={currentUser?.id}
        isMessagePending={controller.messageMutation.isPending}
        canDeactivateUsers={controller.canDeactivateUsers}
        canHardDeleteUsers={controller.canHardDeleteUsers}
      />

      <PendingInvitationsSection
        invitations={controller.pendingInvitations}
        isLoading={controller.invitationsQuery.isLoading}
        onOpenInviteDialog={() => controller.setShowInviteDialog(true)}
        onPreviewInvitation={controller.setPreviewInvitation}
        onResendInvitation={(invitationId) =>
          controller.resendInvitationMutation.mutate(invitationId)
        }
        onRequestCancelInvitation={controller.requestCancelInvitation}
        isResendPending={controller.resendInvitationMutation.isPending}
        isCancelPending={controller.cancelInvitationMutation.isPending}
      />

      <InvitationEmailPreviewDialog
        open={!!controller.previewInvitation}
        invitation={controller.previewInvitation}
        preview={controller.invitationPreviewQuery.data}
        isLoading={controller.invitationPreviewQuery.isLoading}
        isError={controller.invitationPreviewQuery.isError}
        onRetry={() => void controller.invitationPreviewQuery.refetch()}
        onClose={() => controller.setPreviewInvitation(null)}
      />

      <ConfirmationDialog
        open={!!controller.pendingConfirm}
        title={controller.pendingConfirm?.title ?? ''}
        description={controller.pendingConfirm?.description}
        confirmLabel={controller.pendingConfirm?.confirmLabel ?? 'Confirm'}
        variant={controller.pendingConfirm?.variant ?? 'danger'}
        onConfirm={() => controller.pendingConfirm?.onConfirm()}
        onCancel={() => controller.setPendingConfirm(null)}
      />

      {controller.showCreateDialog ? (
        <UserFormDialog
          title="Create User"
          companies={controller.companies}
          currentUserRole={currentUser?.role || 'viewer'}
          onSubmit={(data) => controller.createMutation.mutate(data as UserCreateFormData)}
          onClose={() => controller.setShowCreateDialog(false)}
          isLoading={controller.createMutation.isPending}
        />
      ) : null}

      {editingUser ? (
        <UserFormDialog
          title="Edit User"
          user={editingUser}
          companies={controller.companies}
          currentUserRole={currentUser?.role || 'viewer'}
          onSubmit={(data) =>
            controller.updateMutation.mutate({
              id: editingUser.id,
              data: data as UserUpdateFormData,
            })
          }
          onClose={() => controller.setEditingUser(null)}
          isLoading={controller.updateMutation.isPending}
        />
      ) : null}

      {controller.showInviteDialog ? (
        <InviteUserDialog
          currentUserRole={currentUser?.role || 'viewer'}
          currentUserTenantId={currentUser?.tenant_id}
          onClose={() => controller.setShowInviteDialog(false)}
        />
      ) : null}
    </div>
  )
}
