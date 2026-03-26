import { Building2, Edit2, MessageCircle, Trash2, User as UserIcon } from 'lucide-react'

import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { VirtualizedTable } from '@/components/VirtualizedTable'
import { TableSkeleton } from '@/components/skeletons'
import type { User } from '@/types'

import { getRoleBadgeColor } from '../constants'

interface UsersTableSectionProps {
  users: User[]
  isLoading: boolean
  isError: boolean
  onRetry: () => void
  onOpenCreateDialog: () => void
  onEditUser: (user: User) => void
  onRequestDeactivate: (user: User) => void
  onStartDirectChat: (userId: number) => void
  currentUserId?: number
  isMessagePending: boolean
}

export function UsersTableSection({
  users,
  isLoading,
  isError,
  onRetry,
  onOpenCreateDialog,
  onEditUser,
  onRequestDeactivate,
  onStartDirectChat,
  currentUserId,
  isMessagePending,
}: UsersTableSectionProps) {
  if (isLoading) {
    return <TableSkeleton rows={7} columns={5} />
  }

  if (isError) {
    return (
      <ErrorState
        title="Users could not be loaded"
        message="We could not fetch the current user roster."
        onRetry={onRetry}
      />
    )
  }

  if (users.length === 0) {
    return (
      <EmptyState
        icon={<UserIcon className="h-8 w-8" aria-hidden="true" />}
        title="No users found"
        description="Try adjusting the filters or add a new user to get started."
        action={{ label: 'Add User', onClick: onOpenCreateDialog }}
      />
    )
  }

  return (
    <VirtualizedTable
      items={users}
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
      renderRow={(user) => (
        <>
          <div className="admin-table-cell">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-sky-100">
                <UserIcon className="h-4 w-4 text-sky-600" />
              </div>
              <div className="min-w-0">
                <div className="truncate font-medium text-slate-900 dark:text-slate-100">
                  {user.full_name}
                </div>
                <div className="truncate text-xs text-slate-500 dark:text-slate-400">
                  {user.email}
                </div>
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
            <span
              className={`pill ${
                user.is_active
                  ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200'
                  : 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-200'
              }`}
            >
              {user.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>
          <div className="admin-table-cell">
            <div className="flex items-center justify-end gap-1">
              {user.id !== currentUserId && user.role !== 'viewer' ? (
                <button
                  type="button"
                  onClick={() => onStartDirectChat(user.id)}
                  disabled={isMessagePending}
                  className="admin-icon-action"
                  title="Send message"
                  aria-label={`Send message to ${user.full_name}`}
                >
                  <MessageCircle className="h-4 w-4" />
                </button>
              ) : null}
              <button
                type="button"
                onClick={() => onEditUser(user)}
                className="admin-icon-action"
                title="Edit"
                aria-label={`Edit ${user.full_name}`}
              >
                <Edit2 className="h-4 w-4" />
              </button>
              {user.id !== currentUserId ? (
                <button
                  type="button"
                  onClick={() => onRequestDeactivate(user)}
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
  )
}
