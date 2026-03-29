import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { X } from 'lucide-react'

import { useFocusTrap } from '@/hooks/useAccessibility'
import { api } from '@/lib/api'

interface AssignAgentModalProps {
  ticketId: number
  onClose: () => void
}

export function AssignAgentModal({ ticketId, onClose }: AssignAgentModalProps) {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')

  const { data: users = [] } = useQuery({
    queryKey: ['users', { search }],
    queryFn: () => api.getUsers({ search: search || undefined, is_active: true }),
  })

  const agents = users.filter((user) => user.role !== 'customer')

  const assignMutation = useMutation({
    mutationFn: (agentId: number) =>
      api.assignSupportAgent(ticketId, { agent_id: agentId, is_primary: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['supportTicket', ticketId] })
      queryClient.invalidateQueries({ queryKey: ['supportTickets'] })
      queryClient.invalidateQueries({ queryKey: ['supportTicketSummary'] })
      onClose()
    },
  })

  const { containerRef } = useFocusTrap(onClose)

  return (
    <div className="modal-overlay flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0"
        onClick={onClose}
        aria-label="Close assign agent dialog"
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-label="Assign Agent"
        className="modal-content relative w-full max-w-sm"
      >
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-slate-800">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-slate-100">Assign Agent</h3>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:text-slate-500 dark:hover:text-slate-200"
            aria-label="Close assign agent dialog"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-4">
          <input
            type="text"
            placeholder="Search agents..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="input-field mb-3"
          />
          <div className="max-h-48 space-y-1 overflow-y-auto">
            {agents.map((agent) => (
              <button
                type="button"
                key={agent.id}
                onClick={() => assignMutation.mutate(agent.id)}
                disabled={assignMutation.isPending}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-slate-800"
              >
                <div className="h-7 w-7 rounded-full bg-gray-200 text-center text-xs leading-7 text-gray-600 dark:bg-slate-700 dark:text-slate-300">
                  {(agent.full_name || agent.email).charAt(0).toUpperCase()}
                </div>
                <div>
                  <p className="font-medium text-gray-900 dark:text-slate-100">{agent.full_name}</p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">{agent.role}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
