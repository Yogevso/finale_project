import { formatDistanceToNow } from 'date-fns'
import { ArrowLeft, ArrowRightLeft, UserPlus } from 'lucide-react'

import type { SupportTicketDetail } from '@/types/chat'

import { useSupportTicketDetailController } from '../hooks'
import { AssignAgentModal } from './AssignAgentModal'
import { HandoffModal } from './HandoffModal'
import { SupportMessageList } from './SupportMessageList'
import { SupportReplyComposer } from './SupportReplyComposer'

interface SupportTicketDetailViewProps {
  ticket: SupportTicketDetail
  onBack: () => void
}

export function SupportTicketDetailView({
  ticket,
  onBack,
}: SupportTicketDetailViewProps) {
  const controller = useSupportTicketDetailController(ticket)

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex items-start gap-3">
        <button
          type="button"
          onClick={onBack}
          className="mt-1 rounded-lg p-2 text-gray-400 hover:bg-gray-100 dark:text-slate-500 dark:hover:bg-slate-800"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100">
            {ticket.subject}
          </h2>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500">
            <span>#{ticket.id}</span>
            <span>·</span>
            <span>by {ticket.customer_full_name || 'Unknown'}</span>
            <span>·</span>
            <span>{formatDistanceToNow(new Date(ticket.created_at), { addSuffix: true })}</span>
          </div>
        </div>
        <button
          type="button"
          onClick={() => controller.setShowHandoff(true)}
          className="btn-warning px-3 py-1.5 text-sm"
        >
          <ArrowRightLeft className="h-4 w-4" /> Handoff
        </button>
        <button
          type="button"
          onClick={() => controller.setShowAssign(true)}
          className="btn-secondary px-3 py-1.5 text-sm"
        >
          <UserPlus className="h-4 w-4" /> Assign
        </button>
      </div>

      <SupportMessageList
        ticket={ticket}
        currentUserId={controller.user?.id}
        otherViewerCount={controller.otherViewers.length}
        onUnassignAgent={(agentId) => controller.unassignMutation.mutate(agentId)}
        onUpdatePriority={(priority) => controller.updateMutation.mutate({ priority })}
        onUpdateStatus={(status) => controller.updateMutation.mutate({ status })}
      />

      <div className="surface-card rounded-xl">
        <SupportReplyComposer
          attachmentInputAccept={controller.attachmentInputAccept}
          cannedResponses={controller.cannedQuery.data?.items}
          cannedSearch={controller.cannedSearch}
          canSend={controller.canSend}
          isCannedLoading={controller.cannedQuery.isLoading}
          isInternal={controller.isInternal}
          isSending={controller.sendMutation.isPending}
          message={controller.message}
          messageError={controller.messageError}
          onCannedSearchChange={controller.setCannedSearch}
          onInsertCanned={controller.insertCanned}
          onRemoveSelectedFile={controller.removeSelectedFile}
          onSend={controller.handleSend}
          onSetInternal={controller.setIsInternal}
          onSetMessage={controller.setMessage}
          onSetMessageError={controller.setMessageError}
          onShowCannedChange={controller.setShowCanned}
          onSelectedFileChange={controller.handleSelectedFile}
          selectedFile={controller.selectedFile}
          showCanned={controller.showCanned}
          fileInputRef={controller.fileInputRef}
        />
      </div>

      {controller.showAssign ? (
        <AssignAgentModal ticketId={ticket.id} onClose={() => controller.setShowAssign(false)} />
      ) : null}
      {controller.showHandoff ? (
        <HandoffModal ticketId={ticket.id} onClose={() => controller.setShowHandoff(false)} />
      ) : null}
    </div>
  )
}
