/**
 * AddPeopleModal — add members to an existing group chat (X1-045)
 */

import { useId, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { X, Search, UserPlus } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import type { ChatDetail } from '@/types/chat'
import type { ChatEligibleUser } from '@/types/chat'
import { useFocusTrap } from '@/hooks/useAccessibility'

interface AddPeopleModalProps {
  chat: ChatDetail
  onClose: () => void
}

export default function AddPeopleModal({ chat, onClose }: AddPeopleModalProps) {
  const { user: currentUser } = useAuth()
  const queryClient = useQueryClient()
  const { containerRef } = useFocusTrap(onClose)
  const titleId = useId()
  const [search, setSearch] = useState('')

  const existingUserIds = new Set(chat.participants.map((p) => p.user_id))

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['chatEligibleUsers', { search }],
    queryFn: () => api.getChatEligibleUsers({ search: search || undefined }),
  })

  // Filter out current user and already-in-chat users
  const available = users.filter(
    (u: ChatEligibleUser) => u.id !== currentUser?.id && !existingUserIds.has(u.id),
  )

  const addMutation = useMutation({
    mutationFn: (userId: number) =>
      api.addChatParticipant(chat.id, { user_id: userId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat', chat.id] })
      queryClient.invalidateQueries({ queryKey: ['chats'] })
    },
  })

  return (
    <div className="modal-overlay flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0"
        onClick={onClose}
        aria-label="Close add people dialog"
        tabIndex={-1}
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="modal-content motion-enter-scale relative w-full max-w-md dark:bg-slate-900"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-slate-800">
          <h2 id={titleId} className="text-lg font-semibold text-gray-900 dark:text-slate-100">Add People</h2>
          <button type="button" onClick={onClose} className="rounded-lg p-1 text-gray-400 hover:text-gray-600 dark:text-slate-500 dark:hover:text-slate-200" aria-label="Close add people dialog">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Search */}
        <div className="px-6 py-3">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search users..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-gray-300 py-2 pl-9 pr-3 text-sm focus:border-blue-500 focus:outline-none"
              aria-label="Search people"
            />
          </div>
        </div>

        {/* User list */}
        <div className="max-h-64 overflow-y-auto px-2 pb-4">
          {isLoading ? (
            <p className="px-4 py-8 text-center text-sm text-gray-400">Loading...</p>
          ) : available.length === 0 ? (
            <p className="px-4 py-8 text-center text-sm text-gray-400">
              {search ? 'No matching users' : 'All users are already in this chat'}
            </p>
          ) : (
            available.map((u: ChatEligibleUser) => (
              <div
                key={u.id}
                className="flex items-center gap-3 rounded-lg px-4 py-2.5 hover:bg-gray-50"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-200 text-xs font-medium text-gray-600">
                  {(u.full_name || u.email).charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-gray-900">{u.full_name}</p>
                  <p className="truncate text-xs text-gray-500">{u.email}</p>
                </div>
                <button
                  type="button"
                  onClick={() => addMutation.mutate(u.id)}
                  disabled={addMutation.isPending}
                  className="flex items-center gap-1 rounded-lg bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-600 hover:bg-blue-100 disabled:opacity-50"
                >
                  <UserPlus className="h-3.5 w-3.5" />
                  Add
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
