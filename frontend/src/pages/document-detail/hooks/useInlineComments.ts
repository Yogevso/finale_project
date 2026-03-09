import { useCallback, useState } from 'react'
import type { MouseEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { queryKeys } from '@/lib/queryKeys'

export interface SelectionPopupState {
  show: boolean
  x: number
  y: number
  text: string
}

export interface CommentPopupState {
  show: boolean
  x: number
  y: number
  text: string
  anchorId: string
}

const EMPTY_SELECTION_POPUP: SelectionPopupState = { show: false, x: 0, y: 0, text: '' }
const EMPTY_COMMENT_POPUP: CommentPopupState = { show: false, x: 0, y: 0, text: '', anchorId: '' }

export function useInlineComments(documentId: number) {
  const queryClient = useQueryClient()
  const [selectionPopup, setSelectionPopup] = useState<SelectionPopupState>(EMPTY_SELECTION_POPUP)
  const [commentPopup, setCommentPopup] = useState<CommentPopupState>(EMPTY_COMMENT_POPUP)
  const [commentText, setCommentText] = useState('')
  const [isPrivateComment, setIsPrivateComment] = useState(false)
  const [isSubmittingComment, setIsSubmittingComment] = useState(false)

  const createCommentMutation = useMutation({
    mutationFn: (data: { content: string; is_private?: boolean; anchor_text?: string; anchor_id?: string }) =>
      api.createComment(documentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.comments.byDocument(documentId) })
      setCommentPopup(EMPTY_COMMENT_POPUP)
      setCommentText('')
      setIsPrivateComment(false)
      setIsSubmittingComment(false)
    },
    onError: () => {
      setIsSubmittingComment(false)
    },
  })

  const handleMouseUp = useCallback(
    (event: MouseEvent) => {
      if ((event.target as HTMLElement).closest('.inline-comment-popup')) {
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
      anchorId: `anchor-${Date.now()}`,
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
    })
  }, [commentPopup.anchorId, commentPopup.text, commentText, createCommentMutation, isPrivateComment])

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
