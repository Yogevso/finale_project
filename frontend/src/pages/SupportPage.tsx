import { ListSkeleton } from '@/components/skeletons'
import { ErrorState } from '@/components/ErrorState'
import PageHeader from '@/components/PageHeader'
import { SupportTicketDetailView, SupportTicketsList } from '@/pages/support/components'
import { useSupportPageController } from '@/pages/support/hooks'

export default function SupportPage() {
  const controller = useSupportPageController()

  if (controller.activeTicketId && controller.ticketQuery.isLoading) {
    return (
      <div className="space-y-4">
        <PageHeader title="Support" subtitle="Manage support tickets and feedback conversations" />
        <div className="mx-4 mb-4">
          <ListSkeleton rows={5} />
        </div>
      </div>
    )
  }

  if (controller.activeTicketId && controller.ticketQuery.isError) {
    return (
      <div className="space-y-4">
        <PageHeader title="Support" subtitle="Manage support tickets and feedback conversations" />
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
        <PageHeader title="Support" subtitle="Manage support tickets and feedback conversations" />
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
      <PageHeader title="Support" subtitle="Manage support tickets and feedback conversations" />
      <SupportTicketsList
        tickets={controller.tickets}
        isLoading={controller.ticketsQuery.isLoading}
        isError={controller.ticketsQuery.isError}
        onRetry={() => void controller.ticketsQuery.refetch()}
        statusFilter={controller.statusFilter}
        onStatusFilterChange={controller.setStatusFilter}
        onOpenTicket={controller.setActiveTicketId}
      />
    </div>
  )
}
