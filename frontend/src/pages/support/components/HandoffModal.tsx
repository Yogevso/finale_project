import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { X } from 'lucide-react'

import { useFocusTrap } from '@/hooks/useAccessibility'
import { api } from '@/lib/api'

interface HandoffModalProps {
  ticketId: number
  onClose: () => void
}

export function HandoffModal({ ticketId, onClose }: HandoffModalProps) {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [note, setNote] = useState('')
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(null)

  const { data: users = [] } = useQuery({
    queryKey: ['users', { search }],
    queryFn: () => api.getUsers({ search: search || undefined, is_active: true }),
  })

  const agents = users.filter((user) => user.role !== 'customer')

  const handoffMutation = useMutation({
    mutationFn: () => api.handoffTicket(ticketId, selectedAgentId!, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['supportTicket', ticketId] })
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
        aria-label="Close handoff dialog"
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-label="Handoff Ticket"
        className="modal-content relative w-full max-w-sm"
      >
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-slate-800">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-slate-100">Handoff Ticket</h3>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:text-slate-500 dark:hover:text-slate-200"
            aria-label="Close handoff dialog"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="space-y-3 p-4">
          <input
            type="text"
            placeholder="Search agents..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="input-field"
          />
          <div className="max-h-36 space-y-1 overflow-y-auto">
            {agents.map((agent) => (
              <button
                type="button"
                key={agent.id}
                onClick={() => setSelectedAgentId(agent.id)}
                className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                  selectedAgentId === agent.id
                    ? 'bg-orange-50 ring-1 ring-orange-300 dark:bg-orange-950/30 dark:ring-orange-900/70'
                    : 'hover:bg-gray-50 dark:hover:bg-slate-800'
                }`}
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
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Handoff note (optional)..."
            rows={2}
            className="input-field min-h-[5rem] resize-none"
          />
          <button
            type="button"
            onClick={() => handoffMutation.mutate()}
            disabled={!selectedAgentId || handoffMutation.isPending}
            className="w-full rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600 disabled:opacity-50"
          >
            {handoffMutation.isPending ? 'Handing off...' : 'Confirm Handoff'}
          </button>
        </div>
      </div>
    </div>
  )
}
