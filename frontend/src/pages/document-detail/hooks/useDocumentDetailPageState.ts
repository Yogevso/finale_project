import { useCallback, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { getAudienceDirtyState } from '@/features/documents'
import { isOverdueDueDate } from '@/lib/documentDueDates'
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
      detail?: unknown
      error_code?: string
      message?: unknown
    }
  }
  message?: unknown
}

const UNKNOWN_DOCUMENT_KEY = 'unknown'

const extractErrorText = (value: unknown): string | null => {
  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed.length > 0 ? trimmed : null
  }

  if (value && typeof value === 'object') {
    const nestedValue = value as {
      detail?: unknown
      message?: unknown
      error?: unknown
    }

    return (
      extractErrorText(nestedValue.detail) ||
      extractErrorText(nestedValue.message) ||
      extractErrorText(nestedValue.error)
    )
  }

  return null
}

const getMutationErrorMessage = (error: unknown, fallback: string) =>
  extractErrorText((error as ApiMutationError)?.response?.data?.detail) ||
  extractErrorText((error as ApiMutationError)?.response?.data?.message) ||
  extractErrorText((error as ApiMutationError)?.message) ||
  fallback

const getVisibilityUpdateErrorMessage = (error: unknown) => {
  const errorCode = (error as ApiMutationError)?.response?.data?.error_code
  if (errorCode === 'missing_company_assignment') {
    return 'Company visibility requires at least one assigned company. Use "Assign Companies" in Details first.'
  }
  if (errorCode === 'invalid_company_set') {
    return 'Visibility and company assignment are inconsistent. Update assignments and try again.'
  }
  return getMutationErrorMessage(error, 'Failed to update document')
}

const getAssignmentMutationErrorMessage = (error: unknown) => {
  const errorCode = (error as ApiMutationError)?.response?.data?.error_code
  if (errorCode === 'precondition_required') {
    return 'This document changed since your last view. Refresh and try assignment again.'
  }
  if (errorCode === 'conflict') {
    return 'Assignment update conflict detected. Refresh to get the latest document state and retry.'
  }
  if (errorCode === 'missing_company_assignment') {
    return 'Company-visible documents must keep at least one assigned company.'
  }
  if (errorCode === 'invalid_company_set') {
    return 'One or more selected companies are invalid for this document.'
  }
  return getMutationErrorMessage(error, 'Failed to update company assignments')
}

export function useDocumentDetailPageState() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const { isEditor, isManager } = useAuth()
  const queryClient = useQueryClient()

  const [isEditing, setIsEditing] = useState(false)
  const [activeTab, setActiveTabState] = useState<DocumentDetailTab>('preview')
  const [scrollProgress, setScrollProgress] = useState<number>(0)
  const [pendingAnchor, setPendingAnchor] = useState<PendingAnchor | null>(null)
  const [contentEditRequestToken, setContentEditRequestToken] = useState(0)
  const [showCompanySelector, setShowCompanySelector] = useState(false)
  const [assignmentDraftIds, setAssignmentDraftIds] = useState<number[] | null>(null)
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
  const audienceAccessPreview = detailPageBundle?.audience_access_preview
  const reviewHistoryItems = detailPageBundle?.review_history.items ?? []
  const assignedCompanyIds = useMemo(
    () => assignedCompanies.map((company) => company.id),
    [assignedCompanies],
  )
  const assignmentDraftCompanyIds = assignmentDraftIds ?? assignedCompanyIds
  const assignmentDirtyState = useMemo(
    () =>
      getAudienceDirtyState(
        {
          visibility: document?.visibility ?? 'internal',
          company_ids: assignedCompanyIds,
        },
        {
          visibility: document?.visibility ?? 'internal',
          company_ids: assignmentDraftCompanyIds,
        },
      ),
    [assignedCompanyIds, assignmentDraftCompanyIds, document?.visibility],
  )
  const hasUnsavedAssignmentChanges =
    showCompanySelector && assignmentDirtyState.companyAssignmentsChanged

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
    onError: (mutationError: unknown) => {
      alert(getVisibilityUpdateErrorMessage(mutationError))
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

  const archiveMutation = useMutation({
    mutationFn: () => api.archiveDocument(documentId),
    onSuccess: () => {
      invalidateDocumentDetailState()
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all })
    },
    onError: (mutationError: unknown) => {
      alert(getMutationErrorMessage(mutationError, 'Failed to archive document'))
    },
  })

  const restoreMutation = useMutation({
    mutationFn: () => api.restoreDocument(documentId),
    onSuccess: () => {
      invalidateDocumentDetailState()
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all })
    },
    onError: (mutationError: unknown) => {
      alert(getMutationErrorMessage(mutationError, 'Failed to restore document'))
    },
  })

  const assignCompaniesMutation = useMutation({
    mutationFn: (companyIds: number[]) => {
      const ifMatch = document?.etag || (document?.row_version ? String(document.row_version) : '')
      if (!ifMatch) {
        throw new Error('Document is missing a concurrency token; refresh and try again.')
      }
      return api.assignCompanies(documentId, companyIds, ifMatch)
    },
    onSuccess: () => {
      invalidateDocumentDetailState()
      setShowCompanySelector(false)
      setAssignmentDraftIds(null)
    },
    onError: (mutationError: unknown) => {
      alert(getAssignmentMutationErrorMessage(mutationError))
    },
  })

  const removeCompanyMutation = useMutation({
    mutationFn: (companyId: number) => {
      const ifMatch = document?.etag || (document?.row_version ? String(document.row_version) : '')
      if (!ifMatch) {
        throw new Error('Document is missing a concurrency token; refresh and try again.')
      }
      return api.removeCompanyAssignment(documentId, companyId, ifMatch)
    },
    onSuccess: () => {
      invalidateDocumentDetailState()
    },
    onError: (mutationError: unknown) => {
      alert(getAssignmentMutationErrorMessage(mutationError))
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

  useEffect(() => {
    if (!hasUnsavedAssignmentChanges) {
      return
    }

    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ''
      return ''
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [hasUnsavedAssignmentChanges])

  const confirmDiscardUnsavedAssignments = useCallback(() => {
    if (!hasUnsavedAssignmentChanges) {
      return true
    }
    return confirm('You have unsaved company assignment changes. Discard them?')
  }, [hasUnsavedAssignmentChanges])

  const resetAssignmentDraft = useCallback(() => {
    setAssignmentDraftIds(assignedCompanyIds)
  }, [assignedCompanyIds])

  const closeCompanySelector = useCallback(
    (options?: { force?: boolean }) => {
      if (!options?.force && !confirmDiscardUnsavedAssignments()) {
        return false
      }
      setShowCompanySelector(false)
      setAssignmentDraftIds(null)
      return true
    },
    [confirmDiscardUnsavedAssignments],
  )

  const applyWidth = useCallback((value: ReadingWidth) => {
    setContentWidth(value)
    setReadingWidth(value)
  }, [])

  const handleScrollProgress = useCallback((progress: number) => {
    setScrollProgress(progress)
  }, [])

  const navigateToDocuments = useCallback(() => {
    if (!confirmDiscardUnsavedAssignments()) {
      return
    }
    navigate('/documents')
  }, [confirmDiscardUnsavedAssignments, navigate])

  const navigateToFullscreen = useCallback(() => {
    if (!confirmDiscardUnsavedAssignments()) {
      return
    }
    if (!id) {
      navigate('/documents')
      return
    }
    navigate(`/documents/${id}/fullscreen`)
  }, [confirmDiscardUnsavedAssignments, id, navigate])

  const navigateToDetail = useCallback(() => {
    if (!confirmDiscardUnsavedAssignments()) {
      return
    }
    if (!id) {
      navigate('/documents')
      return
    }
    navigate(`/documents/${id}`)
  }, [confirmDiscardUnsavedAssignments, id, navigate])

  const handleDelete = useCallback(() => {
    if (!confirmDiscardUnsavedAssignments()) {
      return
    }
    if (confirm('Are you sure you want to delete this document?')) {
      deleteMutation.mutate()
    }
  }, [confirmDiscardUnsavedAssignments, deleteMutation])

  const handleArchive = useCallback(() => {
    if (!confirmDiscardUnsavedAssignments()) {
      return
    }
    if (!confirm(`Archive "${document?.title || 'this document'}"? You can restore it later.`)) {
      return
    }
    archiveMutation.mutate()
  }, [archiveMutation, confirmDiscardUnsavedAssignments, document?.title])

  const handleRestore = useCallback(() => {
    if (!confirmDiscardUnsavedAssignments()) {
      return
    }
    restoreMutation.mutate()
  }, [confirmDiscardUnsavedAssignments, restoreMutation])

  const exportCalendar = useCallback(async () => {
    try {
      const payload = await api.getDocumentCalendarExport(documentId)
      const blob = new Blob([payload.ical], { type: payload.content_type })
      const objectUrl = window.URL.createObjectURL(blob)
      const anchor = window.document.createElement('a')
      anchor.href = objectUrl
      anchor.download = payload.filename
      window.document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      window.URL.revokeObjectURL(objectUrl)
    } catch (exportError) {
      alert(getMutationErrorMessage(exportError, 'Failed to export due date calendar'))
    }
  }, [documentId])

  const handleEditAction = useCallback(() => {
    if (activeTab === 'details') {
      if (isEditing) {
        setIsEditing(false)
        return
      }
      if (showCompanySelector && !closeCompanySelector()) {
        return
      }
      setIsEditing(true)
      return
    }

    setIsEditing(false)
    setActiveTabState('preview')
    setContentEditRequestToken((previous) => previous + 1)
  }, [activeTab, closeCompanySelector, isEditing, showCompanySelector])

  const setActiveTab = useCallback(
    (nextTab: DocumentDetailTab) => {
      if (nextTab === activeTab) {
        return true
      }

      const isLeavingDetailsTab = activeTab === 'details' && nextTab !== 'details'
      if (isLeavingDetailsTab) {
        if (!confirmDiscardUnsavedAssignments()) {
          return false
        }
        if (showCompanySelector) {
          closeCompanySelector({ force: true })
        }
        setIsEditing(false)
      }

      setActiveTabState(nextTab)
      return true
    },
    [activeTab, closeCompanySelector, confirmDiscardUnsavedAssignments, showCompanySelector],
  )

  const toggleCompanySelector = useCallback(() => {
    if (showCompanySelector) {
      closeCompanySelector()
      return
    }
    setAssignmentDraftIds(assignedCompanyIds)
    setShowCompanySelector(true)
  }, [assignedCompanyIds, closeCompanySelector, showCompanySelector])

  const updateAssignmentDraft = useCallback((companyIds: number[]) => {
    setAssignmentDraftIds(companyIds)
  }, [])

  const discardAssignmentDraft = useCallback(() => {
    resetAssignmentDraft()
  }, [resetAssignmentDraft])

  const saveAssignmentDraft = useCallback(() => {
    const companyIds = assignmentDraftIds ?? assignedCompanyIds
    if (!assignmentDirtyState.companyAssignmentsChanged) {
      closeCompanySelector({ force: true })
      return
    }
    if (companyIds.some((companyId) => !Number.isInteger(companyId) || companyId <= 0)) {
      alert('One or more selected companies are invalid for this document.')
      return
    }
    if (document?.visibility === 'company' && companyIds.length === 0) {
      alert('Company-visible documents must keep at least one assigned company.')
      return
    }
    assignCompaniesMutation.mutate(companyIds)
  }, [
    assignedCompanyIds,
    assignmentDirtyState.companyAssignmentsChanged,
    assignmentDraftIds,
    assignCompaniesMutation,
    closeCompanySelector,
    document?.visibility,
  ])

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
  const isOverdue = isOverdueDueDate(document?.due_date)

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
    assignmentDraftCompanyIds,
    hasUnsavedAssignmentChanges,
    updateAssignmentDraft,
    saveAssignmentDraft,
    discardAssignmentDraft,
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
    audienceAccessPreview,
    reviewHistoryItems,
    navigateToDocuments,
    navigateToFullscreen,
    navigateToDetail,
    exportCalendar,
    handleArchive,
    handleDelete,
    handleEditAction,
    handleRestore,
    isArchivingDocument: archiveMutation.isPending,
    isOverdue,
    isRestoringDocument: restoreMutation.isPending,
    updateDocument: updateMutation.mutate,
    isUpdatingDocument: updateMutation.isPending,
    isAssigningCompanies: assignCompaniesMutation.isPending,
    removeCompany: removeCompanyMutation.mutate,
    isRemovingCompany: removeCompanyMutation.isPending,
    isSubmittingReview: submitReviewMutation.isPending,
  }
}
