import { useCallback, useMemo, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { queryKeys } from '@/lib/queryKeys'
import {
  useDocumentDetailPageBundleQuery,
} from '@/hooks/useDocumentQueries'
import { getReadingWidth, setReadingWidth, type ReadingWidth } from '@/lib/readingWidth'
import type { DocumentUpdate } from '@/types'

export type DocumentDetailTab = 'preview' | 'details' | 'versions' | 'attachments' | 'comments'

export interface PendingAnchor {
  text: string
  id: string
}

interface ApiMutationError {
  response?: {
    data?: {
      detail?: string
    }
  }
  message?: string
}

const UNKNOWN_DOCUMENT_KEY = 'unknown'

const getMutationErrorMessage = (error: unknown, fallback: string) =>
  (error as ApiMutationError)?.response?.data?.detail ||
  (error as ApiMutationError)?.message ||
  fallback

export function useDocumentDetailPageState() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const { isEditor, isManager } = useAuth()
  const queryClient = useQueryClient()

  const [isEditing, setIsEditing] = useState(false)
  const [activeTab, setActiveTab] = useState<DocumentDetailTab>('preview')
  const [scrollProgress, setScrollProgress] = useState<number>(0)
  const [pendingAnchor, setPendingAnchor] = useState<PendingAnchor | null>(null)
  const [contentEditRequestToken, setContentEditRequestToken] = useState(0)
  const [showCompanySelector, setShowCompanySelector] = useState(false)
  const [showSubmitReview, setShowSubmitReview] = useState(false)
  const [submitMessage, setSubmitMessage] = useState('')
  const [contentWidth, setContentWidth] = useState<ReadingWidth>(() => getReadingWidth('reading'))

  const documentIdKey = id ?? UNKNOWN_DOCUMENT_KEY
  const documentId = Number(id)

  const isFullscreen =
    location.search.includes('fullscreen=1') || location.pathname.endsWith('/fullscreen')

  const bffQueryKey = queryKeys.bff.documentDetailBundle(documentIdKey)

  const { data: detailPageBundle, isLoading, error } = useDocumentDetailPageBundleQuery(id, {
    refetchInterval: (query) => {
      const items = query.state.data?.attachments ?? []
      const hasPendingPreview = items.some(
        (attachment) =>
          attachment.preview_pdf_status === 'pending' ||
          attachment.preview_pdf_status === 'processing',
      )
      return hasPendingPreview ? 2500 : false
    },
  })

  const document = detailPageBundle?.document

  const attachments = useMemo(
    () => detailPageBundle?.attachments ?? [],
    [detailPageBundle?.attachments],
  )
  const assignedCompanies = detailPageBundle?.assigned_companies ?? []
  const reviewHistoryItems = detailPageBundle?.review_history.items ?? []

  const invalidateDocumentDetailState = () => {
    queryClient.invalidateQueries({ queryKey: bffQueryKey })
    queryClient.invalidateQueries({ queryKey: queryKeys.documents.detail(documentIdKey) })
  }

  const updateMutation = useMutation({
    mutationFn: (data: DocumentUpdate) => {
      const ifMatch = document?.etag || (document?.row_version ? String(document.row_version) : '')
      if (!ifMatch) {
        throw new Error('Document is missing a concurrency token; refresh and try again.')
      }
      return api.updateDocument(documentId, data, ifMatch)
    },
    onSuccess: () => {
      invalidateDocumentDetailState()
      setIsEditing(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteDocument(documentId),
    onSuccess: () => {
      navigate('/documents')
    },
    onError: (mutationError: unknown) => {
      console.error('Delete error:', mutationError)
      alert(getMutationErrorMessage(mutationError, 'Failed to delete document'))
    },
  })

  const assignCompaniesMutation = useMutation({
    mutationFn: (companyIds: number[]) => api.assignCompanies(documentId, companyIds),
    onSuccess: () => {
      invalidateDocumentDetailState()
      setShowCompanySelector(false)
    },
  })

  const removeCompanyMutation = useMutation({
    mutationFn: (companyId: number) => api.removeCompanyAssignment(documentId, companyId),
    onSuccess: () => {
      invalidateDocumentDetailState()
    },
  })

  const submitReviewMutation = useMutation({
    mutationFn: (message?: string) => api.submitForReview(documentId, { message }),
    onSuccess: () => {
      invalidateDocumentDetailState()
      queryClient.invalidateQueries({ queryKey: queryKeys.reviews.all })
      setShowSubmitReview(false)
      setSubmitMessage('')
    },
  })

  const applyWidth = useCallback((value: ReadingWidth) => {
    setContentWidth(value)
    setReadingWidth(value)
  }, [])

  const handleScrollProgress = useCallback((progress: number) => {
    setScrollProgress(progress)
  }, [])

  const navigateToDocuments = useCallback(() => {
    navigate('/documents')
  }, [navigate])

  const navigateToFullscreen = useCallback(() => {
    if (!id) {
      navigate('/documents')
      return
    }
    navigate(`/documents/${id}/fullscreen`)
  }, [id, navigate])

  const navigateToDetail = useCallback(() => {
    if (!id) {
      navigate('/documents')
      return
    }
    navigate(`/documents/${id}`)
  }, [id, navigate])

  const handleDelete = useCallback(() => {
    if (confirm('Are you sure you want to delete this document?')) {
      deleteMutation.mutate()
    }
  }, [deleteMutation])

  const handleEditAction = useCallback(() => {
    if (activeTab === 'details') {
      if (isEditing) {
        setIsEditing(false)
        return
      }
      setIsEditing(true)
      return
    }

    setIsEditing(false)
    setActiveTab('preview')
    setContentEditRequestToken((previous) => previous + 1)
  }, [activeTab, isEditing])

  const toggleCompanySelector = useCallback(() => {
    setShowCompanySelector((previous) => !previous)
  }, [])

  const openSubmitReview = useCallback(() => {
    setShowSubmitReview(true)
  }, [])

  const closeSubmitReview = useCallback(() => {
    setShowSubmitReview(false)
    setSubmitMessage('')
  }, [])

  const submitReview = useCallback(() => {
    submitReviewMutation.mutate(submitMessage || undefined)
  }, [submitMessage, submitReviewMutation])

  const clearPendingAnchor = useCallback(() => {
    setPendingAnchor(null)
  }, [])

  const contentWidthClass = contentWidth === 'fluid' ? 'max-w-none' : 'max-w-5xl'
  const readingModeClass = contentWidth === 'reading' ? 'reading-mode' : ''

  const submitReviewErrorMessage = submitReviewMutation.isError
    ? getMutationErrorMessage(submitReviewMutation.error, 'Error submitting for review. Please try again.')
    : null

  return {
    id,
    documentId,
    document,
    isLoading,
    error,
    isEditor,
    isManager,
    isFullscreen,
    isEditing,
    setIsEditing,
    activeTab,
    setActiveTab,
    scrollProgress,
    handleScrollProgress,
    pendingAnchor,
    clearPendingAnchor,
    contentEditRequestToken,
    showCompanySelector,
    toggleCompanySelector,
    showSubmitReview,
    submitMessage,
    setSubmitMessage,
    openSubmitReview,
    closeSubmitReview,
    submitReview,
    submitReviewErrorMessage,
    contentWidth,
    contentWidthClass,
    readingModeClass,
    applyWidth,
    attachments,
    assignedCompanies,
    reviewHistoryItems,
    navigateToDocuments,
    navigateToFullscreen,
    navigateToDetail,
    handleDelete,
    handleEditAction,
    updateDocument: updateMutation.mutate,
    isUpdatingDocument: updateMutation.isPending,
    assignCompanies: assignCompaniesMutation.mutate,
    isAssigningCompanies: assignCompaniesMutation.isPending,
    removeCompany: removeCompanyMutation.mutate,
    isRemovingCompany: removeCompanyMutation.isPending,
    isSubmittingReview: submitReviewMutation.isPending,
  }
}
