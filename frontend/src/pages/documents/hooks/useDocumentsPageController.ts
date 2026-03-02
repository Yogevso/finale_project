import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'

import {
  buildDocumentsListQueryParams,
  documentsUseCases,
  requiresVisibilityChangeConfirmation,
} from '@/features/documents'
import { useAuth } from '@/lib/auth'
import { queryKeys } from '@/lib/queryKeys'
import type { DocumentStatus, DocumentVisibility } from '@/types'

type VisibilityChangeRequest = {
  id: number
  currentVisibility: DocumentVisibility
  nextVisibility: DocumentVisibility
  ifMatch: string
  title: string
}

type ApiMutationError = {
  response?: {
    data?: {
      detail?: string
      error_code?: string
    }
  }
  message?: string
}

const getVisibilityUpdateErrorMessage = (error: unknown) => {
  const apiError = error as ApiMutationError
  const errorCode = apiError.response?.data?.error_code
  if (errorCode === 'missing_company_assignment') {
    return 'Company visibility requires at least one assigned company. Open the document details and assign companies first.'
  }
  if (errorCode === 'invalid_company_set') {
    return 'This visibility change conflicts with company assignment rules. Adjust assignments and try again.'
  }
  return apiError.response?.data?.detail || apiError.message || 'Failed to update visibility.'
}

export function useDocumentsPageController() {
  const { isEditor, isManager } = useAuth()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()

  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<DocumentStatus | ''>('')
  const [visibilityFilter, setVisibilityFilter] = useState<DocumentVisibility | ''>('')
  const statusDetailsRef = useRef<HTMLDetailsElement>(null)
  const visibilityDetailsRef = useRef<HTMLDetailsElement>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [showQuickStartModal, setShowQuickStartModal] = useState(false)
  const [visibilityOverrides, setVisibilityOverrides] = useState<Record<number, DocumentVisibility>>(
    {},
  )
  const [pendingVisibilityChange, setPendingVisibilityChange] =
    useState<VisibilityChangeRequest | null>(null)

  const action = searchParams.get('action')
  const isQuickCreateMode = action === 'create'

  useEffect(() => {
    if (isQuickCreateMode) {
      setShowQuickStartModal(true)
    }
  }, [isQuickCreateMode])

  const listQueryParams = buildDocumentsListQueryParams({
    page,
    pageSize: 10,
    search,
    statusFilter,
    visibilityFilter,
  })

  const documentsQuery = useQuery({
    queryKey: queryKeys.documents.list(listQueryParams),
    queryFn: () => documentsUseCases.listDocuments(listQueryParams),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => documentsUseCases.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all })
    },
    onError: (error: unknown) => {
      const apiError = error as { response?: { data?: { detail?: string } }; message?: string }
      console.error('Delete error:', error)
      alert(
        apiError.response?.data?.detail ||
          apiError.message ||
          'Failed to delete document. You may need Manager or Admin role.',
      )
    },
  })

  const visibilityMutation = useMutation({
    mutationFn: ({
      id,
      visibility,
      ifMatch,
      companyIds,
    }: {
      id: number
      visibility: DocumentVisibility
      ifMatch: string
      companyIds?: number[]
    }) => documentsUseCases.updateVisibility(id, visibility, ifMatch, companyIds),
    onSuccess: (_, variables) => {
      setVisibilityOverrides((prev) => {
        const next = { ...prev }
        delete next[variables.id]
        return next
      })
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all })
    },
    onError: (error: unknown, variables) => {
      setVisibilityOverrides((prev) => {
        const next = { ...prev }
        delete next[variables.id]
        return next
      })
      alert(getVisibilityUpdateErrorMessage(error))
    },
  })

  const handleDelete = (id: number, title: string) => {
    if (!isManager) {
      return
    }
    if (confirm(`Are you sure you want to delete "${title}"?`)) {
      deleteMutation.mutate(id)
    }
  }

  const handleVisibilityChange = (change: VisibilityChangeRequest) => {
    setVisibilityOverrides((prev) => ({ ...prev, [change.id]: change.nextVisibility }))

    // Always show dialog when changing to company visibility (to select companies)
    // or when expanding access requires confirmation
    if (
      change.nextVisibility === 'company' ||
      requiresVisibilityChangeConfirmation(change.currentVisibility, change.nextVisibility)
    ) {
      setPendingVisibilityChange(change)
      return
    }

    visibilityMutation.mutate({
      id: change.id,
      visibility: change.nextVisibility,
      ifMatch: change.ifMatch,
    })
  }

  const confirmPendingVisibilityChange = (companyIds?: number[]) => {
    if (!pendingVisibilityChange) {
      return
    }
    const change = pendingVisibilityChange
    setPendingVisibilityChange(null)
    visibilityMutation.mutate({
      id: change.id,
      visibility: change.nextVisibility,
      ifMatch: change.ifMatch,
      companyIds,
    })
  }

  const cancelPendingVisibilityChange = () => {
    if (!pendingVisibilityChange) {
      return
    }
    const pendingId = pendingVisibilityChange.id
    setPendingVisibilityChange(null)
    setVisibilityOverrides((prev) => {
      const next = { ...prev }
      delete next[pendingId]
      return next
    })
  }

  return {
    isEditor,
    isManager,
    page,
    setPage,
    search,
    setSearch,
    statusFilter,
    setStatusFilter,
    visibilityFilter,
    setVisibilityFilter,
    statusDetailsRef,
    visibilityDetailsRef,
    showCreateModal,
    setShowCreateModal,
    showUploadModal,
    setShowUploadModal,
    showQuickStartModal,
    setShowQuickStartModal,
    visibilityOverrides,
    pendingVisibilityChange,
    isQuickCreateMode,
    documentsQuery,
    deleteMutation,
    visibilityMutation,
    handleDelete,
    handleVisibilityChange,
    confirmPendingVisibilityChange,
    cancelPendingVisibilityChange,
  }
}
