/**
 * ChatHeader — active chat header with actions menu (X1-030)
 */

import { useState, useRef, useEffect } from 'react'
import { X, Users, UserPlus, Trash2, MoreVertical, Info, LogOut, Search, BellOff, Bell, Settings } from 'lucide-react'
import type { ChatDetail, ChatParticipant } from '@/types/chat'
import { useAuth } from '@/lib/auth'

interface ChatHeaderProps {
  chat: ChatDetail | null
  displayName: string
  typingText: string
  isConnected: boolean
  onClose: () => void
  onDeleteChat?: () => void
  onAddPeople?: () => void
  onLeaveChat?: () => void
  onSearch?: () => void
  onMuteToggle?: () => void
  isMuted?: boolean
  onOpenSettings?: () => void
}

export default function ChatHeader({
  chat,
  displayName,
  typingText,
  isConnected,
  onClose,
  onDeleteChat,
  onAddPeople,
  onLeaveChat,
  onSearch,
  onMuteToggle,
  isMuted,
  onOpenSettings,
}: ChatHeaderProps) {
  const { user } = useAuth()
  const [showMenu, setShowMenu] = useState(false)
  const [showMembers, setShowMembers] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  const participantCount = chat?.participants?.length ?? 0
  const isOwner = chat?.participants?.some(
    (p) => p.user_id === user?.id && p.role === 'owner',
  )
  const isGroup = chat?.type === 'group'

  // Close menu on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowMenu(false)
      }
    }
    if (showMenu) document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [showMenu])

  return (
    <div className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3">
      <div className="flex items-center gap-3 min-w-0">
        {/* Avatar */}
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-blue-100 text-sm font-semibold text-blue-600">
          {displayName.charAt(0).toUpperCase()}
        </div>
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-gray-900">{displayName}</h3>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            {typingText ? (
              <span className="italic text-blue-500">{typingText}</span>
            ) : isGroup ? (
              <button
                onClick={() => setShowMembers(!showMembers)}
                className="flex items-center gap-1 hover:text-gray-700 transition-colors"
              >
                <Users className="h-3 w-3" />
                {participantCount} members
              </button>
            ) : (
              <span className="flex items-center gap-1">
                <span className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-gray-300'}`} />
                {isConnected ? 'Online' : 'Connecting...'}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-1">
        {/* Search button (X1-043) */}
        {onSearch && (
          <button
            onClick={onSearch}
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
            title="Search messages"
          >
            <Search className="h-5 w-5" />
          </button>
        )}

        {/* Actions menu */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          >
            <MoreVertical className="h-5 w-5" />
          </button>

          {showMenu && (
            <div className="absolute right-0 top-full mt-1 w-52 rounded-xl border border-gray-200 bg-white py-1 shadow-lg z-50">
              {/* View members */}
              <button
                onClick={() => { setShowMembers(!showMembers); setShowMenu(false) }}
                className="flex w-full items-center gap-2.5 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                <Info className="h-4 w-4 text-gray-400" />
                {showMembers ? 'Hide members' : 'View members'}
              </button>

              {/* Add people (group chats, owner/admin only) */}
              {isGroup && isOwner && onAddPeople && (
                <button
                  onClick={() => { onAddPeople(); setShowMenu(false) }}
                  className="flex w-full items-center gap-2.5 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  <UserPlus className="h-4 w-4 text-gray-400" />
                  Add people
                </button>
              )}

              {/* Mute toggle (X1-025) */}
              {onMuteToggle && (
                <button
                  onClick={() => { onMuteToggle(); setShowMenu(false) }}
                  className="flex w-full items-center gap-2.5 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  {isMuted ? <Bell className="h-4 w-4 text-gray-400" /> : <BellOff className="h-4 w-4 text-gray-400" />}
                  {isMuted ? 'Unmute chat' : 'Mute chat'}
                </button>
              )}

              {/* Group settings (X1-045/046) */}
              {isGroup && isOwner && onOpenSettings && (
                <button
                  onClick={() => { onOpenSettings(); setShowMenu(false) }}
                  className="flex w-full items-center gap-2.5 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  <Settings className="h-4 w-4 text-gray-400" />
                  Group settings
                </button>
              )}

              {/* Leave chat (group, non-owner) */}
              {isGroup && !isOwner && onLeaveChat && (
                <button
                  onClick={() => { onLeaveChat(); setShowMenu(false) }}
                  className="flex w-full items-center gap-2.5 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                >
                  <LogOut className="h-4 w-4" />
                  Leave group
                </button>
              )}

              <div className="my-1 border-t border-gray-100" />

              {/* Delete chat */}
              {onDeleteChat && (
                <button
                  onClick={() => { onDeleteChat(); setShowMenu(false) }}
                  className="flex w-full items-center gap-2.5 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                >
                  <Trash2 className="h-4 w-4" />
                  Delete chat
                </button>
              )}
            </div>
          )}
        </div>

        <button
          onClick={onClose}
          className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Members panel */}
      {showMembers && chat?.participants && (
        <div className="absolute right-16 top-16 w-64 rounded-xl border border-gray-200 bg-white shadow-lg z-40 overflow-hidden">
          <div className="border-b border-gray-100 px-4 py-2.5">
            <h4 className="text-sm font-semibold text-gray-900">
              Members ({participantCount})
            </h4>
          </div>
          <div className="max-h-64 overflow-y-auto py-1">
            {chat.participants.map((p: ChatParticipant) => (
              <div
                key={p.id}
                className="flex items-center gap-3 px-4 py-2 hover:bg-gray-50"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-200 text-xs font-medium text-gray-600">
                  {(p.user_full_name || '?').charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-gray-900">
                    {p.user_full_name || `User #${p.user_id}`}
                    {p.user_id === user?.id && (
                      <span className="ml-1.5 text-xs text-gray-400">(you)</span>
                    )}
                  </p>
                  <p className="text-xs text-gray-500 capitalize">{p.role}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
