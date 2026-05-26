import { useCallback, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { queryKeys } from '@/lib/queryKeys'
import type { Comment } from '@/types'

export interface SelectionPopupState {
  show: boolean
  x: number
  y: number
  text: string
  anchorId: string
}

export interface CommentPopupState {
  show: boolean
  x: number
  y: number
  text: string
  anchorId: string
}

interface MouseUpTargetEvent {
  target: EventTarget | null
}

const EMPTY_SELECTION_POPUP: SelectionPopupState = {
  show: false,
  x: 0,
  y: 0,
  text: '',
  anchorId: '',
}
const EMPTY_COMMENT_POPUP: CommentPopupState = { show: false, x: 0, y: 0, text: '', anchorId: '' }

function resolveAnchorId(selection: Selection): string {
  if (selection.rangeCount === 0) {
    return 'document-content-area'
  }

  const range = selection.getRangeAt(0)
  const node = range.commonAncestorContainer
  const baseElement = (node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement) as
    | HTMLElement
    | null

  if (!baseElement) {
    return 'document-content-area'
  }

  const contentRoot = baseElement.closest<HTMLElement>('#document-content-area')
  if (!contentRoot) {
    return 'document-content-area'
  }

  const directHeading = baseElement.closest<HTMLElement>('h1[id], h2[id], h3[id], h4[id], h5[id], h6[id]')
  if (directHeading?.id) {
    return directHeading.id
  }

  const headings = Array.from(
    contentRoot.querySelectorAll<HTMLElement>('h1[id], h2[id], h3[id], h4[id], h5[id], h6[id]'),
  )
  const nodeType = baseElement.ownerDocument.defaultView?.Node ?? Node
  let fallbackHeadingId: string | null = null

  for (const heading of headings) {
    if (heading === baseElement || heading.contains(baseElement)) {
      fallbackHeadingId = heading.id
      break
    }
    const relation = heading.compareDocumentPosition(baseElement)
    if (relation & nodeType.DOCUMENT_POSITION_FOLLOWING) {
      fallbackHeadingId = heading.id
      continue
    }
    if (relation & nodeType.DOCUMENT_POSITION_PRECEDING) {
      break
    }
  }

  if (fallbackHeadingId) {
    return fallbackHeadingId
  }

  return headings[0]?.id || 'document-content-area'
}

export function useInlineComments(documentId: number, reviewId: number | null = null) {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const [selectionPopup, setSelectionPopup] = useState<SelectionPopupState>(EMPTY_SELECTION_POPUP)
  const [commentPopup, setCommentPopup] = useState<CommentPopupState>(EMPTY_COMMENT_POPUP)
  const [commentText, setCommentText] = useState('')
  const [isPrivateComment, setIsPrivateComment] = useState(false)
  const [isSubmittingComment, setIsSubmittingComment] = useState(false)

  const createCommentMutation = useMutation({
    mutationFn: (data: {
      content: string
      is_private?: boolean
      anchor_text?: string
      anchor_id?: string
      review_id?: number
    }) =>
      api.createComment(documentId, data),
    onMutate: async (data) => {
      await queryClient.cancelQueries({
        queryKey: queryKeys.comments.byDocument(documentId, reviewId),
      })

      const previousComments = queryClient.getQueryData<Comment[]>(
        queryKeys.comments.byDocument(documentId, reviewId),
      )
      const optimisticId = -Date.now()
      const nowIso = new Date().toISOString()
      const optimisticComment: Comment = {
        id: optimisticId,
        document_id: documentId,
        user_id: user?.id || 0,
        review_id: data.review_id ?? null,
        author_id: user?.id,
        author_name: user?.full_name || user?.username || 'You',
        parent_id: null,
        content: data.content,
        is_private: !!data.is_private,
        anchor_text: data.anchor_text ?? null,
        anchor_id: data.anchor_id ?? null,
        is_resolved: false,
        created_at: nowIso,
        updated_at: nowIso,
        user: user
          ? {
              id: user.id,
              username: user.username,
              full_name: user.full_name,
              role: user.role,
            }
          : undefined,
        replies: [],
        reply_count: 0,
        chat_id: null,
      }

      queryClient.setQueryData<Comment[]>(
        queryKeys.comments.byDocument(documentId, reviewId),
        (current) =>
          current ? [optimisticComment, ...current] : [optimisticComment],
      )

      const previousCommentPopup = commentPopup
      const previousCommentText = commentText
      const previousIsPrivateComment = isPrivateComment

      setCommentPopup(EMPTY_COMMENT_POPUP)
      setCommentText('')
      setIsPrivateComment(false)
      setIsSubmittingComment(false)
      window.getSelection()?.removeAllRanges()

      return {
        optimisticId,
        previousComments,
        previousCommentPopup,
        previousCommentText,
        previousIsPrivateComment,
      }
    },
    onSuccess: (createdComment, _variables, context) => {
      queryClient.setQueryData<Comment[]>(
        queryKeys.comments.byDocument(documentId, reviewId),
        (current) => {
          if (!current) return [createdComment]
          return current.map((comment) =>
            comment.id === context?.optimisticId ? createdComment : comment,
          )
        },
      )
      void queryClient.invalidateQueries({
        queryKey: queryKeys.comments.byDocument(documentId, reviewId),
      })
    },
    onError: (_error, _variables, context) => {
      if (context) {
        queryClient.setQueryData(
          queryKeys.comments.byDocument(documentId, reviewId),
          context.previousComments,
        )
      }
      setCommentPopup(context?.previousCommentPopup ?? EMPTY_COMMENT_POPUP)
      setCommentText(context?.previousCommentText ?? '')
      setIsPrivateComment(context?.previousIsPrivateComment ?? false)
      setIsSubmittingComment(false)
    },
  })

  const handleMouseUp = useCallback(
    (event: MouseUpTargetEvent) => {
      const eventTarget = event.target as HTMLElement | null
      if (eventTarget?.closest('.inline-comment-popup')) {
        return
      }

      const selection = window.getSelection()
      if (!selection || selection.isCollapsed) {
        if (!commentPopup.show) {
          setSelectionPopup(EMPTY_SELECTION_POPUP)
        }
        return
      }

      const selectedText = selection.toString().trim()
      if (selectedText.length >= 3) {
        const range = selection.getRangeAt(0)
        const rect = range.getBoundingClientRect()
        setSelectionPopup({
          show: true,
          x: rect.left + rect.width / 2,
          y: rect.top - 10,
          text: selectedText,
          anchorId: resolveAnchorId(selection),
        })
      } else {
        setSelectionPopup(EMPTY_SELECTION_POPUP)
      }
    },
    [commentPopup.show],
  )

  const handleOpenCommentForm = useCallback(() => {
    if (!selectionPopup.text) return

    setCommentPopup({
      show: true,
      x: selectionPopup.x,
      y: selectionPopup.y + 60,
      text: selectionPopup.text,
      anchorId: selectionPopup.anchorId || 'document-content-area',
    })
    setSelectionPopup(EMPTY_SELECTION_POPUP)
  }, [selectionPopup])

  const handleSubmitComment = useCallback(() => {
    if (!commentText.trim()) return
    setIsSubmittingComment(true)
    createCommentMutation.mutate({
      content: commentText.trim(),
      is_private: isPrivateComment,
      anchor_text: commentPopup.text,
      anchor_id: commentPopup.anchorId,
      review_id: reviewId ?? undefined,
    })
  }, [
    commentPopup.anchorId,
    commentPopup.text,
    commentText,
    createCommentMutation,
    isPrivateComment,
    reviewId,
  ])

  const handleCloseCommentPopup = useCallback(() => {
    setSelectionPopup(EMPTY_SELECTION_POPUP)
    setCommentPopup(EMPTY_COMMENT_POPUP)
    setCommentText('')
    setIsPrivateComment(false)
    window.getSelection()?.removeAllRanges()
  }, [])

  return {
    selectionPopup,
    commentPopup,
    commentText,
    isPrivateComment,
    isSubmittingComment,
    setCommentText,
    setIsPrivateComment,
    handleMouseUp,
    handleOpenCommentForm,
    handleSubmitComment,
    handleCloseCommentPopup,
  }
}
