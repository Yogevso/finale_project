import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { queryKeys } from '@/lib/queryKeys'
import { useDocumentCommentsQuery } from '@/hooks/useDocumentQueries'

interface CommentUser {
  id: number
  username: string
  full_name?: string
  role: string
}

interface Comment {
  id: number
  document_id: number
  user_id: number
  parent_id?: number | null
  content: string
  is_private: boolean
  anchor_text?: string | null
  anchor_id?: string | null
  is_resolved: boolean
  created_at: string
  updated_at: string
  user?: CommentUser
  replies: Comment[]
  reply_count: number
}

interface CommentCreate {
  content: string
  is_private?: boolean
  anchor_text?: string
  anchor_id?: string
  parent_id?: number
}

interface CommentsSectionProps {
  documentId: number
  pendingAnchor?: { text: string; id: string } | null
  onClearAnchor?: () => void
}

export default function CommentsSection({ documentId, pendingAnchor, onClearAnchor }: CommentsSectionProps) {
  const { user, isEditor } = useAuth()
  const queryClient = useQueryClient()
  const [newComment, setNewComment] = useState('')
  const [isPrivate, setIsPrivate] = useState(false)
  const [replyingTo, setReplyingTo] = useState<number | null>(null)
  const [replyText, setReplyText] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editText, setEditText] = useState('')
  const [showResolved, setShowResolved] = useState(false)

  const { data: comments = [], isLoading } = useDocumentCommentsQuery(documentId)

  const createMutation = useMutation({
    mutationFn: (data: CommentCreate) => api.createComment(documentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.comments.byDocument(documentId) })
      setNewComment('')
      setIsPrivate(false)
      setReplyingTo(null)
      setReplyText('')
      onClearAnchor?.()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ commentId, data }: { commentId: number; data: { content?: string; is_resolved?: boolean } }) =>
      api.updateComment(documentId, commentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.comments.byDocument(documentId) })
      setEditingId(null)
      setEditText('')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (commentId: number) => api.deleteComment(documentId, commentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.comments.byDocument(documentId) })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (newComment.trim()) {
      createMutation.mutate({
        content: newComment.trim(),
        is_private: isPrivate,
        anchor_text: pendingAnchor?.text,
        anchor_id: pendingAnchor?.id,
      })
    }
  }

  const handleReply = (parentId: number, parentIsPrivate: boolean) => {
    if (replyText.trim()) {
      createMutation.mutate({
        content: replyText.trim(),
        parent_id: parentId,
        is_private: parentIsPrivate, // Replies inherit privacy from parent
      })
    }
  }

  const handleUpdate = (commentId: number) => {
    if (editText.trim()) {
      updateMutation.mutate({ commentId, data: { content: editText.trim() } })
    }
  }

  const handleResolve = (commentId: number, resolved: boolean) => {
    updateMutation.mutate({ commentId, data: { is_resolved: resolved } })
  }

  // Filter comments
  const filteredComments = (comments as Comment[]).filter(c => showResolved || !c.is_resolved)

  // Separate inline comments (with anchor) from general comments
  const inlineComments = filteredComments.filter(c => c.anchor_text)
  const generalComments = filteredComments.filter(c => !c.anchor_text)

  // Count stats
  const totalCount = (comments as Comment[]).length
  const unresolvedCount = (comments as Comment[]).filter(c => !c.is_resolved && !c.parent_id).length
  const privateCount = (comments as Comment[]).filter(c => c.is_private && !c.parent_id).length

  if (isLoading) {
    return <div className="animate-pulse bg-slate-100 h-32 rounded-xl"></div>
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      {/* Header with stats */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-slate-900">
            Comments
          </h2>
          <div className="flex gap-2">
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
                🔒 {privateCount} private
              </span>
            )}
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={showResolved}
            onChange={(e) => setShowResolved(e.target.checked)}
            className="rounded border-slate-300"
          />
          Show resolved
        </label>
      </div>

      {/* New Comment Form */}
      {user && (
        <form onSubmit={handleSubmit} className="mb-6">
          {/* Inline comment indicator */}
          {pendingAnchor && (
            <div className="mb-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-xs font-medium text-amber-700">📍 Commenting on selected text:</span>
                  <p className="text-sm text-amber-800 mt-1 italic">"{pendingAnchor.text.slice(0, 100)}{pendingAnchor.text.length > 100 ? '...' : ''}"</p>
                </div>
                <button
                  type="button"
                  onClick={onClearAnchor}
                  className="text-amber-600 hover:text-amber-800"
                >
                  ✕
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
                onChange={(e) => setNewComment(e.target.value)}
                placeholder={pendingAnchor ? "Add your comment about this section..." : "Add a comment..."}
                className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-sky-500 focus:border-sky-500 resize-none"
                rows={2}
              />
              <div className="mt-2 flex items-center justify-between">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={isPrivate}
                    onChange={(e) => setIsPrivate(e.target.checked)}
                    className="rounded border-slate-300 text-purple-600 focus:ring-purple-500"
                  />
                  <span className="text-slate-600">
                    🔒 Private <span className="text-xs text-slate-400">(only admins/editors can see)</span>
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

      {/* Inline Comments Section */}
      {inlineComments.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium text-slate-700 mb-3 flex items-center gap-2">
            <span>📍 Inline Comments</span>
            <span className="text-xs text-slate-400">({inlineComments.length})</span>
          </h3>
          <div className="space-y-3">
            {inlineComments.map((comment) => (
              <CommentThread
                key={comment.id}
                comment={comment}
                currentUserId={user?.id}
                isEditor={isEditor}
                replyingTo={replyingTo}
                replyText={replyText}
                editingId={editingId}
                editText={editText}
                onReplyStart={() => { setReplyingTo(comment.id); setReplyText(''); }}
                onReplyCancel={() => { setReplyingTo(null); setReplyText(''); }}
                onReplyChange={setReplyText}
                onReplySubmit={() => handleReply(comment.id, comment.is_private)}
                onEditStart={(id, content) => { setEditingId(id); setEditText(content); }}
                onEditCancel={() => { setEditingId(null); setEditText(''); }}
                onEditChange={setEditText}
                onEditSubmit={handleUpdate}
                onDelete={(id) => { if (confirm('Delete this comment?')) deleteMutation.mutate(id); }}
                onResolve={handleResolve}
                isPending={createMutation.isPending || updateMutation.isPending}
              />
            ))}
          </div>
        </div>
      )}

      {/* General Comments Section */}
      <div>
        {inlineComments.length > 0 && generalComments.length > 0 && (
          <h3 className="text-sm font-medium text-slate-700 mb-3 flex items-center gap-2">
            <span>💬 General Comments</span>
            <span className="text-xs text-slate-400">({generalComments.length})</span>
          </h3>
        )}
        
        {generalComments.length === 0 && inlineComments.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-4xl mb-2">💬</div>
            <p className="text-slate-500 text-sm">No comments yet</p>
            <p className="text-slate-400 text-xs mt-1">Be the first to comment</p>
          </div>
        ) : generalComments.length === 0 ? null : (
          <div className="space-y-4">
            {generalComments.map((comment) => (
              <CommentThread
                key={comment.id}
                comment={comment}
                currentUserId={user?.id}
                isEditor={isEditor}
                replyingTo={replyingTo}
                replyText={replyText}
                editingId={editingId}
                editText={editText}
                onReplyStart={() => { setReplyingTo(comment.id); setReplyText(''); }}
                onReplyCancel={() => { setReplyingTo(null); setReplyText(''); }}
                onReplyChange={setReplyText}
                onReplySubmit={() => handleReply(comment.id, comment.is_private)}
                onEditStart={(id, content) => { setEditingId(id); setEditText(content); }}
                onEditCancel={() => { setEditingId(null); setEditText(''); }}
                onEditChange={setEditText}
                onEditSubmit={handleUpdate}
                onDelete={(id) => { if (confirm('Delete this comment?')) deleteMutation.mutate(id); }}
                onResolve={handleResolve}
                isPending={createMutation.isPending || updateMutation.isPending}
              />
            ))}
          </div>
        )}
      </div>
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
}: {
  comment: Comment
  currentUserId?: number
  isEditor: boolean
  replyingTo: number | null
  replyText: string
  editingId: number | null
  editText: string
  onReplyStart: () => void
  onReplyCancel: () => void
  onReplyChange: (text: string) => void
  onReplySubmit: () => void
  onEditStart: (id: number, content: string) => void
  onEditCancel: () => void
  onEditChange: (text: string) => void
  onEditSubmit: (id: number) => void
  onDelete: (id: number) => void
  onResolve: (id: number, resolved: boolean) => void
  isPending: boolean
}) {
  const isReplying = replyingTo === comment.id
  const isEditing = editingId === comment.id
  const isOwner = currentUserId === comment.user_id
  const canResolve = isEditor

  return (
    <div className={`group rounded-xl border ${comment.is_resolved ? 'bg-slate-50 border-slate-200' : comment.is_private ? 'bg-purple-50 border-purple-200' : 'bg-white border-slate-200'} p-4`}>
      {/* Anchor text preview for inline comments */}
      {comment.anchor_text && (
        <div className="mb-3 text-xs bg-amber-50 text-amber-700 px-2 py-1 rounded border-l-2 border-amber-400">
          <span className="font-medium">Referenced text: </span>
          <span className="italic">"{comment.anchor_text.slice(0, 80)}{comment.anchor_text.length > 80 ? '...' : ''}"</span>
        </div>
      )}

      {/* Comment header */}
      <div className="flex items-start gap-3">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0 ${
          comment.is_private ? 'bg-purple-100 text-purple-700' : 'bg-slate-100 text-slate-600'
        }`}>
          {comment.user?.full_name?.charAt(0) || comment.user?.username?.charAt(0) || '?'}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="font-medium text-slate-900 text-sm">
              {comment.user?.full_name || comment.user?.username || 'Unknown'}
            </span>
            {comment.user?.role && (
              <span className={`text-xs px-1.5 py-0.5 rounded ${
                comment.user.role === 'system_admin' ? 'bg-rose-100 text-rose-700' :
                comment.user.role === 'admin' ? 'bg-purple-100 text-purple-700' :
                comment.user.role === 'manager' ? 'bg-orange-100 text-orange-700' :
                comment.user.role === 'editor' ? 'bg-sky-100 text-sky-700' :
                'bg-slate-100 text-slate-600'
              }`}>
                {comment.user.role.replace('_', ' ')}
              </span>
            )}
            {comment.is_private && (
              <span className="text-xs px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded">
                🔒 Private
              </span>
            )}
            {comment.is_resolved && (
              <span className="text-xs px-1.5 py-0.5 bg-emerald-100 text-emerald-700 rounded">
                ✓ Resolved
              </span>
            )}
            <span className="text-xs text-slate-400">
              {new Date(comment.created_at).toLocaleDateString()} {new Date(comment.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>

          {/* Comment content */}
          {isEditing ? (
            <div>
              <textarea
                value={editText}
                onChange={(e) => onEditChange(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-sky-500 resize-none text-sm"
                rows={2}
              />
              <div className="mt-2 flex gap-2">
                <button onClick={() => onEditSubmit(comment.id)} disabled={!editText.trim() || isPending} className="px-3 py-1 text-xs bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:opacity-50">Save</button>
                <button onClick={onEditCancel} className="px-3 py-1 text-xs text-slate-600 hover:bg-slate-100 rounded-lg">Cancel</button>
              </div>
            </div>
          ) : (
            <p className={`text-sm whitespace-pre-wrap ${comment.is_resolved ? 'text-slate-500' : 'text-slate-700'}`}>{comment.content}</p>
          )}

          {/* Actions */}
          {!isEditing && currentUserId && (
            <div className="mt-2 flex gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
              <button onClick={onReplyStart} className="text-xs text-slate-500 hover:text-sky-600">Reply</button>
              {isOwner && (
                <>
                  <button onClick={() => onEditStart(comment.id, comment.content)} className="text-xs text-slate-500 hover:text-sky-600">Edit</button>
                  <button onClick={() => onDelete(comment.id)} className="text-xs text-slate-500 hover:text-rose-600">Delete</button>
                </>
              )}
              {canResolve && !comment.parent_id && (
                <button 
                  onClick={() => onResolve(comment.id, !comment.is_resolved)} 
                  className={`text-xs ${comment.is_resolved ? 'text-orange-500 hover:text-orange-600' : 'text-emerald-500 hover:text-emerald-600'}`}
                >
                  {comment.is_resolved ? 'Reopen' : 'Resolve'}
                </button>
              )}
            </div>
          )}

          {/* Reply Form */}
          {isReplying && (
            <div className="mt-3 pl-4 border-l-2 border-sky-200">
              <textarea
                value={replyText}
                onChange={(e) => onReplyChange(e.target.value)}
                placeholder="Write a reply..."
                className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-sky-500 resize-none text-sm"
                rows={2}
                autoFocus
              />
              <div className="mt-2 flex gap-2">
                <button onClick={onReplySubmit} disabled={!replyText.trim() || isPending} className="px-3 py-1 text-xs bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:opacity-50">Reply</button>
                <button onClick={onReplyCancel} className="px-3 py-1 text-xs text-slate-600 hover:bg-slate-100 rounded-lg">Cancel</button>
              </div>
            </div>
          )}

          {/* Replies */}
          {comment.replies && comment.replies.length > 0 && (
            <div className="mt-4 pl-4 border-l-2 border-slate-200 space-y-3">
              {comment.replies.map((reply) => (
                <div key={reply.id} className="flex gap-2 group/reply">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium flex-shrink-0 ${
                    reply.is_private ? 'bg-purple-100 text-purple-600' : 'bg-slate-100 text-slate-500'
                  }`}>
                    {reply.user?.full_name?.charAt(0) || reply.user?.username?.charAt(0) || '?'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                      <span className="font-medium text-slate-900 text-sm">{reply.user?.full_name || reply.user?.username || 'Unknown'}</span>
                      {reply.user?.role && ['system_admin', 'admin', 'manager', 'editor'].includes(reply.user.role) && (
                        <span className={`text-xs px-1 py-0.5 rounded ${
                          reply.user.role === 'system_admin' ? 'bg-rose-100 text-rose-700' :
                          reply.user.role === 'admin' ? 'bg-purple-100 text-purple-700' :
                          reply.user.role === 'manager' ? 'bg-orange-100 text-orange-700' :
                          'bg-sky-100 text-sky-700'
                        }`}>
                          {reply.user.role.replace('_', ' ')}
                        </span>
                      )}
                      <span className="text-xs text-slate-400">{new Date(reply.created_at).toLocaleDateString()}</span>
                    </div>

                    {editingId === reply.id ? (
                      <div>
                        <textarea value={editText} onChange={(e) => onEditChange(e.target.value)} className="w-full px-2 py-1 border border-slate-200 rounded focus:ring-2 focus:ring-sky-500 resize-none text-sm" rows={2} />
                        <div className="mt-1 flex gap-2">
                          <button onClick={() => onEditSubmit(reply.id)} disabled={!editText.trim() || isPending} className="px-2 py-0.5 text-xs bg-sky-600 text-white rounded hover:bg-sky-700 disabled:opacity-50">Save</button>
                          <button onClick={onEditCancel} className="px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-100 rounded">Cancel</button>
                        </div>
                      </div>
                    ) : (
                      <p className="text-slate-700 text-sm">{reply.content}</p>
                    )}

                    {editingId !== reply.id && currentUserId === reply.user_id && (
                      <div className="mt-1 flex gap-2 opacity-0 group-hover/reply:opacity-100 transition-opacity">
                        <button onClick={() => onEditStart(reply.id, reply.content)} className="text-xs text-slate-500 hover:text-sky-600">Edit</button>
                        <button onClick={() => onDelete(reply.id)} className="text-xs text-slate-500 hover:text-rose-600">Delete</button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
