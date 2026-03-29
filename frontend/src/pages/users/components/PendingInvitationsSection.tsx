import { Building2, Clock, Eye, Mail, RefreshCw, XCircle } from 'lucide-react'

import { EmptyState } from '@/components/EmptyState'
import { TableSkeleton } from '@/components/skeletons'
import type { Invitation } from '@/types'

import { getInvitationDeliveryBadgeColor, getRoleBadgeColor } from '../constants'

interface PendingInvitationsSectionProps {
  invitations: Invitation[]
  isLoading: boolean
  onOpenInviteDialog: () => void
  onPreviewInvitation: (invitation: Invitation) => void
  onResendInvitation: (invitationId: number) => void
  onRequestCancelInvitation: (invitation: Invitation) => void
  isResendPending: boolean
  isCancelPending: boolean
}

function formatDeliveryDetails(invitation: Invitation): string {
  if (invitation.email_delivery_status === 'failed') {
    return invitation.email_last_error || 'Last delivery attempt failed.'
  }
  if (invitation.email_delivery_status === 'sent' && invitation.email_last_sent_at) {
    return `Sent ${new Date(invitation.email_last_sent_at).toLocaleString()}`
  }
  if (invitation.email_delivery_status === 'suppressed') {
    return 'Delivery is suppressed by the current email configuration.'
  }
  if (invitation.email_last_attempted_at) {
    return `Last checked ${new Date(invitation.email_last_attempted_at).toLocaleString()}`
  }
  return 'Queued for delivery.'
}

function formatSender(invitation: Invitation): string | null {
  if (!invitation.email_last_sender_email) {
    return null
  }
  if (invitation.email_last_sender_name) {
    return `${invitation.email_last_sender_name} <${invitation.email_last_sender_email}>`
  }
  return invitation.email_last_sender_email
}

export function PendingInvitationsSection({
  invitations,
  isLoading,
  onOpenInviteDialog,
  onPreviewInvitation,
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
        <TableSkeleton rows={3} columns={7} />
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
                <th>Email Status</th>
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
                    <div className="space-y-1">
                      <span
                        className={`pill capitalize ${getInvitationDeliveryBadgeColor(invitation.email_delivery_status)}`}
                      >
                        {invitation.email_delivery_status}
                      </span>
                      <p className="max-w-xs text-xs text-slate-500 dark:text-slate-400">
                        {formatDeliveryDetails(invitation)}
                      </p>
                      {formatSender(invitation) ? (
                        <p className="max-w-xs truncate text-xs text-slate-400 dark:text-slate-500">
                          {formatSender(invitation)}
                        </p>
                      ) : null}
                    </div>
                  </td>
                  <td className="admin-table-cell">
                    <span className="text-sm text-slate-500 dark:text-slate-400">
                      {new Date(invitation.expires_at).toLocaleDateString()}
                    </span>
                  </td>
                  <td className="admin-table-cell text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        type="button"
                        onClick={() => onPreviewInvitation(invitation)}
                        className="admin-icon-action"
                        title="Preview Invitation Email"
                        aria-label={`Preview invitation email for ${invitation.email}`}
                      >
                        <Eye className="h-4 w-4" />
                      </button>
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
