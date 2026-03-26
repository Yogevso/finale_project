import { Building2, Clock, Mail, RefreshCw, XCircle } from 'lucide-react'

import { EmptyState } from '@/components/EmptyState'
import { TableSkeleton } from '@/components/skeletons'
import type { Invitation } from '@/types'

import { getRoleBadgeColor } from '../constants'

interface PendingInvitationsSectionProps {
  invitations: Invitation[]
  isLoading: boolean
  onOpenInviteDialog: () => void
  onResendInvitation: (invitationId: number) => void
  onRequestCancelInvitation: (invitation: Invitation) => void
  isResendPending: boolean
  isCancelPending: boolean
}

export function PendingInvitationsSection({
  invitations,
  isLoading,
  onOpenInviteDialog,
  onResendInvitation,
  onRequestCancelInvitation,
  isResendPending,
  isCancelPending,
}: PendingInvitationsSectionProps) {
  return (
    <div className="admin-table-shell">
      <div className="border-b border-slate-200 bg-slate-50 px-6 py-4 dark:border-slate-800 dark:bg-slate-950/70">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-amber-600" />
          <h3 className="section-title">Pending Invitations</h3>
          {!isLoading && invitations.length > 0 ? (
            <span className="pill bg-amber-100 text-amber-700 dark:bg-amber-950/30 dark:text-amber-200">
              {invitations.length}
            </span>
          ) : null}
        </div>
      </div>

      {isLoading ? (
        <TableSkeleton rows={3} columns={6} />
      ) : invitations.length === 0 ? (
        <div className="p-6">
          <EmptyState
            icon={<Mail className="h-8 w-8" aria-hidden="true" />}
            title="No pending invitations"
            description="New user invitations will appear here until they are accepted or canceled."
            action={{ label: 'Invite User', onClick: onOpenInviteDialog }}
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
              {invitations.map((invitation) => (
                <tr key={invitation.id} className="admin-table-row">
                  <td className="admin-table-cell">
                    <div className="flex items-center gap-2">
                      <Mail className="h-4 w-4 text-slate-400 dark:text-slate-500" />
                      <span className="text-slate-900 dark:text-slate-100">
                        {invitation.email}
                      </span>
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
                        <Building2 className="h-3 w-3" />
                        {invitation.tenant_name}
                      </div>
                    ) : (
                      <span className="text-sm text-slate-400 dark:text-slate-500">-</span>
                    )}
                  </td>
                  <td className="admin-table-cell body-copy">{invitation.inviter_name || '-'}</td>
                  <td className="admin-table-cell">
                    <span className="text-sm text-slate-500 dark:text-slate-400">
                      {new Date(invitation.expires_at).toLocaleDateString()}
                    </span>
                  </td>
                  <td className="admin-table-cell text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        type="button"
                        onClick={() => onResendInvitation(invitation.id)}
                        disabled={isResendPending}
                        className="admin-icon-action"
                        title="Resend Invitation"
                        aria-label={`Resend invitation to ${invitation.email}`}
                      >
                        <RefreshCw className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => onRequestCancelInvitation(invitation)}
                        disabled={isCancelPending}
                        className="admin-icon-action-danger"
                        title="Cancel Invitation"
                        aria-label={`Cancel invitation for ${invitation.email}`}
                      >
                        <XCircle className="h-4 w-4" />
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
  )
}
