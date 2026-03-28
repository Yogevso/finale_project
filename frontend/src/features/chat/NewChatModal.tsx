/**
 * NewChatModal — create direct or group chat (X1-036 to X1-038)
 */

import { useId, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { X, Search, Users, User as UserIcon } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import type { ChatEligibleUser } from '@/types/chat'
import { useFocusTrap } from '@/hooks/useAccessibility'

interface NewChatModalProps {
  onClose: () => void
  onCreated: (chatId: number) => void
}

export default function NewChatModal({ onClose, onCreated }: NewChatModalProps) {
  const { user: currentUser } = useAuth()
  const queryClient = useQueryClient()
  const { containerRef } = useFocusTrap(onClose)
  const titleId = useId()
  const [tab, setTab] = useState<'direct' | 'group'>('direct')
  const [search, setSearch] = useState('')
  const [groupName, setGroupName] = useState('')
  const [selectedIds, setSelectedIds] = useState<number[]>([])

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['chatEligibleUsers', { search }],
    queryFn: () => api.getChatEligibleUsers({ search: search || undefined }),
  })

  // Filter out current user
  const filteredUsers = users.filter((u: ChatEligibleUser) => u.id !== currentUser?.id)

  const createDirect = useMutation({
    mutationFn: (userId: number) => api.createDirectChat({ user_id: userId }),
    onSuccess: (chat) => {
      queryClient.invalidateQueries({ queryKey: ['chats'] })
      onCreated(chat.id)
    },
  })

  const createGroup = useMutation({
    mutationFn: () => api.createGroupChat({ name: groupName, participant_ids: selectedIds }),
    onSuccess: (chat) => {
      queryClient.invalidateQueries({ queryKey: ['chats'] })
      onCreated(chat.id)
    },
  })

  const toggleUser = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    )
  }

  const isPending = createDirect.isPending || createGroup.isPending

  const formatRoleLabel = (role: ChatEligibleUser['role']) =>
    role === 'customer' ? 'Customer' : role.replace('_', ' ')

  return (
    <div className="modal-overlay flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0"
        onClick={onClose}
        aria-label="Close new conversation dialog"
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
          <h2 id={titleId} className="text-lg font-semibold text-gray-900 dark:text-slate-100">New Conversation</h2>
          <button type="button" onClick={onClose} className="rounded-lg p-1 text-gray-400 hover:text-gray-600 dark:text-slate-500 dark:hover:text-slate-200" aria-label="Close new conversation dialog">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200">
          <button
            type="button"
            className={`flex-1 py-2.5 text-sm font-medium ${
              tab === 'direct'
                ? 'border-b-2 border-sky-600 text-sky-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
            onClick={() => { setTab('direct'); setSelectedIds([]) }}
          >
            <UserIcon className="mr-1.5 inline h-4 w-4" />
            Direct
          </button>
          <button
            type="button"
            className={`flex-1 py-2.5 text-sm font-medium ${
              tab === 'group'
                ? 'border-b-2 border-sky-600 text-sky-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
            onClick={() => { setTab('group'); setSelectedIds([]) }}
          >
            <Users className="mr-1.5 inline h-4 w-4" />
            Group
          </button>
        </div>

        {/* Group name input */}
        {tab === 'group' && (
          <div className="px-6 pt-4">
            <input
              type="text"
              placeholder="Group name"
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
              aria-label="Group name"
            />
          </div>
        )}

        {/* Search */}
        <div className="px-6 py-3">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search people..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-gray-300 py-2 pl-9 pr-3 text-sm focus:border-sky-500 focus:outline-none"
              aria-label="Search people"
            />
          </div>
        </div>

        {/* User list */}
        <div className="max-h-64 overflow-y-auto px-2">
          {isLoading ? (
            <p className="px-4 py-8 text-center text-sm text-gray-400">Loading...</p>
          ) : filteredUsers.length === 0 ? (
            <p className="px-4 py-8 text-center text-sm text-gray-400">No users found</p>
          ) : (
            filteredUsers.map((u: ChatEligibleUser) => (
              <button
                key={u.id}
                type="button"
                onClick={() => {
                  if (tab === 'direct') {
                    createDirect.mutate(u.id)
                  } else {
                    toggleUser(u.id)
                  }
                }}
                disabled={tab === 'direct' && isPending}
                className={`flex w-full items-center gap-3 rounded-lg px-4 py-2.5 text-left transition-colors hover:bg-gray-50 ${
                  selectedIds.includes(u.id) ? 'bg-sky-50' : ''
                }`}
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-200 text-xs font-medium text-gray-600">
                  {(u.full_name || u.email).charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-gray-900">{u.full_name}</p>
                  <div className="flex items-center gap-2">
                    <p className="truncate text-xs text-gray-500">{u.email}</p>
                    <span
                      className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                        u.role === 'customer'
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {formatRoleLabel(u.role)}
                    </span>
                  </div>
                </div>
                {tab === 'group' && selectedIds.includes(u.id) && (
                  <div className="h-5 w-5 rounded-full bg-sky-600 text-center text-xs leading-5 text-white">✓</div>
                )}
              </button>
            ))
          )}
        </div>

        {/* Footer for group creation */}
        {tab === 'group' && (
          <div className="border-t border-gray-200 px-6 py-4">
            <button
              type="button"
              onClick={() => createGroup.mutate()}
              disabled={isPending || selectedIds.length < 1 || !groupName.trim()}
              className="btn-primary w-full disabled:opacity-50"
            >
              {isPending ? 'Creating...' : `Create Group (${selectedIds.length} selected)`}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
