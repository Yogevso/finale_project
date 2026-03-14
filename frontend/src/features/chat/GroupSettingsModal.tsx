/**
 * GroupSettingsModal — rename group, manage members & roles (X1-045/046)
 */

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { X, Crown, Shield, UserMinus, Check } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import type { ChatDetail, ChatParticipant, ChatParticipantRole } from '@/types/chat'

interface GroupSettingsModalProps {
  chat: ChatDetail
  onClose: () => void
}

export default function GroupSettingsModal({ chat, onClose }: GroupSettingsModalProps) {
  const { user: currentUser } = useAuth()
  const queryClient = useQueryClient()
  const [name, setName] = useState(chat.name || '')
  const [nameChanged, setNameChanged] = useState(false)

  const myParticipant = chat.participants.find((p) => p.user_id === currentUser?.id)
  const isOwner = myParticipant?.role === 'owner'
  const isAdmin = myParticipant?.role === 'admin' || isOwner

  const renameMutation = useMutation({
    mutationFn: () => api.updateChat(chat.id, { name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat', chat.id] })
      queryClient.invalidateQueries({ queryKey: ['chats'] })
      setNameChanged(false)
    },
  })

  const roleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: number; role: ChatParticipantRole }) =>
      api.updateParticipantRole(chat.id, userId, { role }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat', chat.id] })
    },
  })

  const removeMutation = useMutation({
    mutationFn: (userId: number) => api.removeChatParticipant(chat.id, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat', chat.id] })
      queryClient.invalidateQueries({ queryKey: ['chats'] })
    },
  })

  const handleRoleToggle = (participant: ChatParticipant) => {
    if (participant.role === 'owner') return
    const newRole: ChatParticipantRole = participant.role === 'admin' ? 'member' : 'admin'
    roleMutation.mutate({ userId: participant.user_id, role: newRole })
  }

  const roleIcon = (role: ChatParticipantRole) => {
    if (role === 'owner') return <Crown className="h-3.5 w-3.5 text-amber-500" />
    if (role === 'admin') return <Shield className="h-3.5 w-3.5 text-blue-500" />
    return null
  }

  const sortedParticipants = [...chat.participants].sort((a, b) => {
    const order: Record<string, number> = { owner: 0, admin: 1, member: 2 }
    return (order[a.role] ?? 3) - (order[b.role] ?? 3)
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-2xl bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">Group Settings</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Rename group */}
        <div className="border-b border-gray-100 px-6 py-4">
          <label className="mb-1.5 block text-xs font-medium text-gray-500 uppercase tracking-wide">
            Group Name
          </label>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={name}
              onChange={(e) => { setName(e.target.value); setNameChanged(true) }}
              disabled={!isAdmin}
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none disabled:bg-gray-50 disabled:text-gray-500"
              placeholder="Group name"
            />
            {isAdmin && nameChanged && name.trim() && (
              <button
                onClick={() => renameMutation.mutate()}
                disabled={renameMutation.isPending}
                className="flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                <Check className="h-4 w-4" />
                Save
              </button>
            )}
          </div>
        </div>

        {/* Members list */}
        <div className="px-6 py-3">
          <h3 className="mb-2 text-xs font-medium text-gray-500 uppercase tracking-wide">
            Members ({chat.participants.length})
          </h3>
        </div>
        <div className="max-h-72 overflow-y-auto px-2 pb-4">
          {sortedParticipants.map((p) => (
            <div
              key={p.id}
              className="flex items-center gap-3 rounded-lg px-4 py-2.5 hover:bg-gray-50"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-200 text-xs font-medium text-gray-600">
                {(p.user_full_name || '?').charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <p className="truncate text-sm font-medium text-gray-900">
                    {p.user_full_name || `User #${p.user_id}`}
                  </p>
                  {roleIcon(p.role)}
                  {p.user_id === currentUser?.id && (
                    <span className="text-xs text-gray-400">(you)</span>
                  )}
                </div>
                <p className="text-xs text-gray-500 capitalize">{p.role}</p>
              </div>

              {/* Actions — only show for admin/owner, not on themselves or the owner */}
              {isAdmin && p.user_id !== currentUser?.id && p.role !== 'owner' && (
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleRoleToggle(p)}
                    disabled={roleMutation.isPending}
                    className="rounded-lg px-2 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50 disabled:opacity-50"
                    title={p.role === 'admin' ? 'Demote to member' : 'Promote to admin'}
                  >
                    {p.role === 'admin' ? 'Demote' : 'Promote'}
                  </button>
                  <button
                    onClick={() => {
                      if (confirm(`Remove ${p.user_full_name || 'this user'} from the group?`)) {
                        removeMutation.mutate(p.user_id)
                      }
                    }}
                    disabled={removeMutation.isPending}
                    className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500 disabled:opacity-50"
                    title="Remove from group"
                  >
                    <UserMinus className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
