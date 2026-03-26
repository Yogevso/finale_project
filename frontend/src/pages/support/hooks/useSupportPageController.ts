import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { api } from '@/lib/api'
import type { SupportTicketStatus } from '@/types/chat'

export function useSupportPageController() {
  const [activeTicketId, setActiveTicketId] = useState<number | null>(null)
  const [statusFilter, setStatusFilter] = useState<SupportTicketStatus | ''>('')

  const ticketsQuery = useQuery({
    queryKey: ['supportTickets', statusFilter],
    queryFn: () =>
      api.getSupportTickets({
        status: statusFilter || undefined,
        page: 1,
        page_size: 50,
      }),
  })

  const ticketQuery = useQuery({
    queryKey: ['supportTicket', activeTicketId],
    queryFn: () => api.getSupportTicket(activeTicketId as number),
    enabled: activeTicketId !== null,
  })

  return {
    activeTicketId,
    setActiveTicketId,
    statusFilter,
    setStatusFilter,
    ticketsQuery,
    ticketQuery,
    tickets: ticketsQuery.data?.items ?? [],
  }
}
