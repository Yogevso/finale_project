import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'

import { api } from '@/lib/api'
import type { SupportTicketStatus } from '@/types/chat'

export function useSupportPageController() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [activeTicketId, setActiveTicketId] = useState<number | null>(null)
  const [statusFilter, setStatusFilter] = useState<SupportTicketStatus | ''>('')

  useEffect(() => {
    const ticketParam = Number(searchParams.get('ticket') || '')
    if (Number.isInteger(ticketParam) && ticketParam > 0) {
      setActiveTicketId(ticketParam)
      return
    }
    setActiveTicketId(null)
  }, [searchParams])

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
    setActiveTicketId: (ticketId: number | null) => {
      setActiveTicketId(ticketId)
      const nextParams = new URLSearchParams(searchParams)
      if (ticketId) {
        nextParams.set('ticket', String(ticketId))
      } else {
        nextParams.delete('ticket')
      }
      setSearchParams(nextParams, { replace: true })
    },
    statusFilter,
    setStatusFilter,
    ticketsQuery,
    ticketQuery,
    tickets: ticketsQuery.data?.items ?? [],
  }
}
