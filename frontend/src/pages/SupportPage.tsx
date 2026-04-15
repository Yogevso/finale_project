import { ListSkeleton } from '@/components/skeletons'
import { ErrorState } from '@/components/ErrorState'
import PageHeader from '@/components/PageHeader'
import { SupportTicketDetailView, SupportTicketsList } from '@/pages/support/components'
import { useSupportPageController } from '@/pages/support/hooks'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { extractApiErrorMessage, useToast } from '@/lib/toast'

export default function SupportPage() {
  const controller = useSupportPageController()
  const queryClient = useQueryClient()
  const toast = useToast()

  const deleteMutation = useMutation({
    mutationFn: (ticketId: number) => api.deleteSupportTicket(ticketId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['supportTickets'] })
      queryClient.invalidateQueries({ queryKey: ['supportTicketSummary'] })
      toast.success('Ticket deleted')
    },
    onError: (error: unknown) => {
      toast.error('Failed to delete ticket', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  if (controller.activeTicketId && controller.ticketQuery.isLoading) {
    return (
      <div className="space-y-4">
        <PageHeader title="Support" subtitle="Manage support tickets and escalated feedback conversations." />
        <div className="mx-4 mb-4">
          <ListSkeleton rows={5} />
        </div>
      </div>
    )
  }

  if (controller.activeTicketId && controller.ticketQuery.isError) {
    return (
      <div className="space-y-4">
        <PageHeader title="Support" subtitle="Manage support tickets and escalated feedback conversations." />
        <div className="mx-4 mb-4">
          <ErrorState
            title="Ticket could not be loaded"
            message="We could not load the selected support ticket."
            onRetry={() => void controller.ticketQuery.refetch()}
          />
        </div>
      </div>
    )
  }

  if (controller.activeTicketId && controller.ticketQuery.data) {
    return (
      <div className="space-y-4">
        <PageHeader title="Support" subtitle="Manage support tickets and escalated feedback conversations." />
        <div className="mx-4 mb-4">
          <SupportTicketDetailView
            ticket={controller.ticketQuery.data}
            onBack={() => controller.setActiveTicketId(null)}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4 animate-fade-in">
      <PageHeader title="Support" subtitle="Manage support tickets and escalated feedback conversations." />
      <SupportTicketsList
        tickets={controller.tickets}
        summary={controller.supportSummary}
        isLoading={controller.ticketsQuery.isLoading}
        isError={controller.ticketsQuery.isError}
        onRetry={() => void controller.ticketsQuery.refetch()}
        statusFilter={controller.statusFilter}
        onStatusFilterChange={controller.setStatusFilter}
        onOpenTicket={controller.setActiveTicketId}
        onDeleteTicket={(id) => deleteMutation.mutate(id)}
      />
    </div>
  )
}
