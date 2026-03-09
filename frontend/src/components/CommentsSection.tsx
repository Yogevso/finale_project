import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Lock,
  MessageSquare,
  MessageSquareQuote,
  Pencil,
  Reply,
  Trash2,
  X,
} from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { useDocumentCommentsQuery } from '@/hooks/useDocumentQueries'
import { queryKeys } from '@/lib/queryKeys'
import type { Comment, CommentCreate } from '@/types'

interface CommentsSectionProps {
  documentId: number
  pendingAnchor?: { text: string; id: string } | null
  onClearAnchor?: () => void
}

const countThreadComments = (comment: Comment): number =>
  1 + comment.replies.reduce((total, reply) => total + countThreadComments(reply), 0)

const countThreadReplies = (comment: Comment): number =>
  comment.replies.reduce((total, reply) => total + 1 + countThreadReplies(reply), 0)

const roleBadgeClassName = (role?: string) => {
  switch (role) {
    case 'system_admin':
      return 'bg-rose-100 text-rose-700'
    case 'admin':
      return 'bg-purple-100 text-purple-700'
    case 'manager':
      return 'bg-orange-100 text-orange-700'
    case 'editor':
      return 'bg-sky-100 text-sky-700'
    default:
      return 'bg-slate-100 text-slate-600'
  }
}

export default function CommentsSection({
  documentId,
  pendingAnchor,
  onClearAnchor,
}: CommentsSectionProps) {
  const { user, isEditor } = useAuth()
  const queryClient = useQueryClient()
  const [newComment, setNewComment] = useState('')
  const [isPrivate, setIsPrivate] = useState(false)
  const [replyingTo, setReplyingTo] = useState<number | null>(null)
  const [replyText, setReplyText] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editText, setEditText] = useState('')
  const [showResolved, setShowResolved] = useState(false)
  const [collapsedThreads, setCollapsedThreads] = useState<Record<number, boolean>>({})

  const { data: comments = [], isLoading } = useDocumentCommentsQuery(documentId)

  const invalidateComments = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.comments.byDocument(documentId) })
  }

  const createMutation = useMutation({
    mutationFn: (data: CommentCreate) => api.createComment(documentId, data),
    onSuccess: () => {
      invalidateComments()
      setNewComment('')
      setIsPrivate(false)
      setReplyingTo(null)
      setReplyText('')
      onClearAnchor?.()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({
      commentId,
      data,
    }: {
      commentId: number
      data: { content?: string; is_resolved?: boolean }
    }) => api.updateComment(documentId, commentId, data),
    onSuccess: () => {
      invalidateComments()
      setEditingId(null)
      setEditText('')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (commentId: number) => api.deleteComment(documentId, commentId),
    onSuccess: () => {
      invalidateComments()
    },
  })

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    if (!newComment.trim()) {
      return
    }

    createMutation.mutate({
      content: newComment.trim(),
      is_private: isPrivate,
      anchor_text: pendingAnchor?.text,
      anchor_id: pendingAnchor?.id,
    })
  }

  const handleReplySubmit = (parentId: number, parentIsPrivate: boolean) => {
    if (!replyText.trim()) {
      return
    }

    createMutation.mutate({
      content: replyText.trim(),
      parent_id: parentId,
      is_private: parentIsPrivate,
    })
  }

  const handleEditSubmit = (commentId: number) => {
    if (!editText.trim()) {
      return
    }
    updateMutation.mutate({ commentId, data: { content: editText.trim() } })
  }

  const handleResolve = (commentId: number, resolved: boolean) => {
    updateMutation.mutate({ commentId, data: { is_resolved: resolved } })
  }

  const toggleCollapsed = (commentId: number) => {
    setCollapsedThreads((previous) => ({
      ...previous,
      [commentId]: !previous[commentId],
    }))
  }

  const filteredComments = comments.filter((comment) => showResolved || !comment.is_resolved)
  const inlineComments = filteredComments.filter((comment) => Boolean(comment.anchor_text))
  const generalComments = filteredComments.filter((comment) => !comment.anchor_text)
  const totalCount = comments.reduce((total, comment) => total + countThreadComments(comment), 0)
  const unresolvedCount = comments.filter((comment) => !comment.is_resolved).length
  const privateCount = comments.filter((comment) => comment.is_private).length

  if (isLoading) {
    return <div className="animate-pulse bg-slate-100 h-32 rounded-xl"></div>
  }

  const sharedThreadProps = {
    currentUserId: user?.id,
    isEditor,
    replyingTo,
    replyText,
    editingId,
    editText,
    collapsedThreads,
    onToggleCollapsed: toggleCollapsed,
    onReplyStart: (commentId: number) => {
      setReplyingTo(commentId)
      setReplyText('')
    },
    onReplyCancel: () => {
      setReplyingTo(null)
      setReplyText('')
    },
    onReplyChange: setReplyText,
    onReplySubmit: handleReplySubmit,
    onEditStart: (commentId: number, content: string) => {
      setEditingId(commentId)
      setEditText(content)
    },
    onEditCancel: () => {
      setEditingId(null)
      setEditText('')
    },
    onEditChange: setEditText,
    onEditSubmit: handleEditSubmit,
    onDelete: (commentId: number) => {
      if (confirm('Delete this comment?')) {
        deleteMutation.mutate(commentId)
      }
    },
    onResolve: handleResolve,
    isPending: createMutation.isPending || updateMutation.isPending || deleteMutation.isPending,
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-slate-900">Comments</h2>
          <div className="flex gap-2 flex-wrap">
            <span className="px-2 py-0.5 text-xs bg-slate-100 text-slate-600 rounded-full">
              {totalCount} total
            </span>
            {unresolvedCount > 0 && (
              <span className="px-2 py-0.5 text-xs bg-orange-100 text-orange-600 rounded-full">
                {unresolvedCount} open
              </span>
            )}
            {isEditor && privateCount > 0 && (
              <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-600 rounded-full">
                {privateCount} private
              </span>
            )}
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={showResolved}
            onChange={(event) => setShowResolved(event.target.checked)}
            className="rounded border-slate-300"
          />
          Show resolved
        </label>
      </div>

      {user && (
        <form onSubmit={handleSubmit} className="mb-6">
          {pendingAnchor && (
            <div className="mb-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <span className="text-xs font-medium text-amber-700">
                    Commenting on selected text
                  </span>
                  <p className="text-sm text-amber-800 mt-1 italic">
                    "{pendingAnchor.text.slice(0, 100)}
                    {pendingAnchor.text.length > 100 ? '...' : ''}"
                  </p>
                </div>
                <button
                  type="button"
                  onClick={onClearAnchor}
                  className="text-amber-600 hover:text-amber-800"
                  title="Clear selection"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <div className="w-8 h-8 bg-sky-100 text-sky-700 rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0">
              {user.full_name?.charAt(0) || user.username?.charAt(0) || '?'}
            </div>
            <div className="flex-1">
              <textarea
                value={newComment}
                onChange={(event) => setNewComment(event.target.value)}
                placeholder={
                  pendingAnchor
                    ? 'Add your comment about this section...'
                    : 'Add a comment...'
                }
                className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-sky-500 focus:border-sky-500 resize-none"
                rows={2}
              />
              <div className="mt-2 flex items-center justify-between">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={isPrivate}
                    onChange={(event) => setIsPrivate(event.target.checked)}
                    className="rounded border-slate-300 text-purple-600 focus:ring-purple-500"
                  />
                  <span className="text-slate-600">
                    Private <span className="text-xs text-slate-400">(staff only)</span>
                  </span>
                </label>
                <button
                  type="submit"
                  disabled={!newComment.trim() || createMutation.isPending}
                  className="px-4 py-1.5 text-sm bg-sky-600 text-white rounded-xl hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {createMutation.isPending ? 'Posting...' : 'Post Comment'}
                </button>
              </div>
            </div>
          </div>
        </form>
      )}

      {inlineComments.length > 0 && (
        <CommentSectionGroup
          title="Inline Comments"
          count={inlineComments.length}
          icon={<MessageSquareQuote className="h-4 w-4 text-amber-600" />}
        >
          {inlineComments.map((comment) => (
            <CommentThread key={comment.id} comment={comment} {...sharedThreadProps} />
          ))}
        </CommentSectionGroup>
      )}

      {generalComments.length > 0 && (
        <CommentSectionGroup
          title="General Comments"
          count={generalComments.length}
          icon={<MessageSquare className="h-4 w-4 text-sky-600" />}
        >
          {generalComments.map((comment) => (
            <CommentThread key={comment.id} comment={comment} {...sharedThreadProps} />
          ))}
        </CommentSectionGroup>
      )}

      {generalComments.length === 0 && inlineComments.length === 0 && (
        <div className="text-center py-8">
          <MessageSquare className="h-10 w-10 mx-auto text-slate-300 mb-2" />
          <p className="text-slate-500 text-sm">No comments yet</p>
          <p className="text-slate-400 text-xs mt-1">Be the first to comment</p>
        </div>
      )}
    </div>
  )
}

function CommentSectionGroup({
  title,
  count,
  icon,
  children,
}: {
  title: string
  count: number
  icon: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <div className="mb-6 last:mb-0">
      <h3 className="text-sm font-medium text-slate-700 mb-3 flex items-center gap-2">
        {icon}
        <span>{title}</span>
        <span className="text-xs text-slate-400">({count})</span>
      </h3>
      <div className="space-y-3">{children}</div>
    </div>
  )
}

function CommentThread({
  comment,
  currentUserId,
  isEditor,
  replyingTo,
  replyText,
  editingId,
  editText,
  collapsedThreads,
  onToggleCollapsed,
  onReplyStart,
  onReplyCancel,
  onReplyChange,
  onReplySubmit,
  onEditStart,
  onEditCancel,
  onEditChange,
  onEditSubmit,
  onDelete,
  onResolve,
  isPending,
  depth = 0,
}: {
  comment: Comment
  currentUserId?: number
  isEditor: boolean
  replyingTo: number | null
  replyText: string
  editingId: number | null
  editText: string
  collapsedThreads: Record<number, boolean>
  onToggleCollapsed: (commentId: number) => void
  onReplyStart: (commentId: number) => void
  onReplyCancel: () => void
  onReplyChange: (text: string) => void
  onReplySubmit: (parentId: number, parentIsPrivate: boolean) => void
  onEditStart: (commentId: number, content: string) => void
  onEditCancel: () => void
  onEditChange: (text: string) => void
  onEditSubmit: (commentId: number) => void
  onDelete: (commentId: number) => void
  onResolve: (commentId: number, resolved: boolean) => void
  isPending: boolean
  depth?: number
}) {
  const isReplying = replyingTo === comment.id
  const isEditing = editingId === comment.id
  const isOwner = currentUserId === comment.user_id
  const canResolve = isEditor && comment.parent_id === null
  const canReply = currentUserId !== undefined && depth < 2
  const isCollapsed = collapsedThreads[comment.id] ?? false
  const totalReplies = comment.reply_count || countThreadReplies(comment)

  return (
    <div
      className={`group rounded-xl border ${
        comment.is_resolved
          ? 'bg-slate-50 border-slate-200'
          : comment.is_private
            ? 'bg-purple-50 border-purple-200'
            : 'bg-white border-slate-200'
      } p-4`}
      style={{ marginLeft: depth === 0 ? 0 : 16 }}
    >
      {comment.anchor_text && (
        <div className="mb-3 text-xs bg-amber-50 text-amber-700 px-2 py-1 rounded border-l-2 border-amber-400">
          <span className="font-medium">Referenced text: </span>
          <span className="italic">
            "{comment.anchor_text.slice(0, 80)}
            {comment.anchor_text.length > 80 ? '...' : ''}"
          </span>
        </div>
      )}

      <div className="flex items-start gap-3">
        <div
          className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0 ${
            comment.is_private ? 'bg-purple-100 text-purple-700' : 'bg-slate-100 text-slate-600'
          }`}
        >
          {comment.user?.full_name?.charAt(0) || comment.user?.username?.charAt(0) || '?'}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="font-medium text-slate-900 text-sm">
              {comment.user?.full_name || comment.user?.username || 'Unknown'}
            </span>
            {comment.user?.role && (
              <span
                className={`text-xs px-1.5 py-0.5 rounded ${roleBadgeClassName(
                  comment.user.role,
                )}`}
              >
                {comment.user.role.replace('_', ' ')}
              </span>
            )}
            {comment.is_private && (
              <span className="text-xs px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded inline-flex items-center gap-1">
                <Lock className="h-3 w-3" />
                Private
              </span>
            )}
            {comment.is_resolved && (
              <span className="text-xs px-1.5 py-0.5 bg-emerald-100 text-emerald-700 rounded inline-flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" />
                Resolved
              </span>
            )}
            {totalReplies > 0 && (
              <span className="text-xs px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded">
                {totalReplies} repl{totalReplies === 1 ? 'y' : 'ies'}
              </span>
            )}
            <span className="text-xs text-slate-400">
              {new Date(comment.created_at).toLocaleDateString()}{' '}
              {new Date(comment.created_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          </div>

          {isEditing ? (
            <div>
              <textarea
                value={editText}
                onChange={(event) => onEditChange(event.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-sky-500 resize-none text-sm"
                rows={2}
              />
              <div className="mt-2 flex gap-2">
                <button
                  onClick={() => onEditSubmit(comment.id)}
                  disabled={!editText.trim() || isPending}
                  className="px-3 py-1 text-xs bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:opacity-50"
                >
                  Save
                </button>
                <button
                  onClick={onEditCancel}
                  className="px-3 py-1 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <p
              className={`text-sm whitespace-pre-wrap ${
                comment.is_resolved ? 'text-slate-500' : 'text-slate-700'
              }`}
            >
              {comment.content}
            </p>
          )}

          {!isEditing && currentUserId && (
            <div className="mt-3 flex flex-wrap gap-3 text-xs">
              {canReply && (
                <button
                  onClick={() => onReplyStart(comment.id)}
                  className="text-slate-500 hover:text-sky-600 inline-flex items-center gap-1"
                >
                  <Reply className="h-3.5 w-3.5" />
                  Reply
                </button>
              )}
              {isOwner && (
                <>
                  <button
                    onClick={() => onEditStart(comment.id, comment.content)}
                    className="text-slate-500 hover:text-sky-600 inline-flex items-center gap-1"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                    Edit
                  </button>
                  <button
                    onClick={() => onDelete(comment.id)}
                    className="text-slate-500 hover:text-rose-600 inline-flex items-center gap-1"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Delete
                  </button>
                </>
              )}
              {canResolve && (
                <button
                  onClick={() => onResolve(comment.id, !comment.is_resolved)}
                  className={`inline-flex items-center gap-1 ${
                    comment.is_resolved
                      ? 'text-orange-500 hover:text-orange-600'
                      : 'text-emerald-500 hover:text-emerald-600'
                  }`}
                >
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  {comment.is_resolved ? 'Reopen' : 'Resolve'}
                </button>
              )}
              {comment.replies.length > 0 && (
                <button
                  onClick={() => onToggleCollapsed(comment.id)}
                  className="text-slate-500 hover:text-slate-700 inline-flex items-center gap-1"
                >
                  {isCollapsed ? (
                    <ChevronRight className="h-3.5 w-3.5" />
                  ) : (
                    <ChevronDown className="h-3.5 w-3.5" />
                  )}
                  {isCollapsed ? 'Show' : 'Hide'} {totalReplies} repl
                  {totalReplies === 1 ? 'y' : 'ies'}
                </button>
              )}
            </div>
          )}

          {isReplying && canReply && (
            <div className="mt-3 pl-4 border-l-2 border-sky-200">
              <textarea
                value={replyText}
                onChange={(event) => onReplyChange(event.target.value)}
                placeholder={depth === 1 ? 'Write a nested reply...' : 'Write a reply...'}
                className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-sky-500 resize-none text-sm"
                rows={2}
                autoFocus
              />
              <div className="mt-2 flex gap-2">
                <button
                  onClick={() => onReplySubmit(comment.id, comment.is_private)}
                  disabled={!replyText.trim() || isPending}
                  className="px-3 py-1 text-xs bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:opacity-50"
                >
                  Reply
                </button>
                <button
                  onClick={onReplyCancel}
                  className="px-3 py-1 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {!isCollapsed && comment.replies.length > 0 && (
            <div className="mt-4 pl-4 border-l-2 border-slate-200 space-y-3">
              {comment.replies.map((reply) => (
                <CommentThread
                  key={reply.id}
                  comment={reply}
                  currentUserId={currentUserId}
                  isEditor={isEditor}
                  replyingTo={replyingTo}
                  replyText={replyText}
                  editingId={editingId}
                  editText={editText}
                  collapsedThreads={collapsedThreads}
                  onToggleCollapsed={onToggleCollapsed}
                  onReplyStart={onReplyStart}
                  onReplyCancel={onReplyCancel}
                  onReplyChange={onReplyChange}
                  onReplySubmit={onReplySubmit}
                  onEditStart={onEditStart}
                  onEditCancel={onEditCancel}
                  onEditChange={onEditChange}
                  onEditSubmit={onEditSubmit}
                  onDelete={onDelete}
                  onResolve={onResolve}
                  isPending={isPending}
                  depth={depth + 1}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
