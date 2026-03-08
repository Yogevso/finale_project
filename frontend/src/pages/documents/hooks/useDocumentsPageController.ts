import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'

import {
  buildDocumentsListQueryParams,
  documentsUseCases,
} from '@/features/documents'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
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

type VisibilityChangeDialogResult = {
  reason: string
  companyIds?: number[]
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
  const debouncedSearch = useDebouncedValue(search, 300)
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
    search: debouncedSearch,
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
      reason,
      companyIds,
    }: {
      id: number
      visibility: DocumentVisibility
      ifMatch: string
      reason: string
      companyIds?: number[]
    }) => documentsUseCases.updateVisibility(id, visibility, ifMatch, reason, companyIds),
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
    if (change.currentVisibility === change.nextVisibility) {
      setVisibilityOverrides((prev) => {
        const next = { ...prev }
        delete next[change.id]
        return next
      })
      return
    }

    setVisibilityOverrides((prev) => ({ ...prev, [change.id]: change.nextVisibility }))

    // Wave T reason-capture policy: all visibility changes require justification.
    setPendingVisibilityChange(change)
  }

  const confirmPendingVisibilityChange = ({ reason, companyIds }: VisibilityChangeDialogResult) => {
    if (!pendingVisibilityChange) {
      return
    }
    const change = pendingVisibilityChange
    setPendingVisibilityChange(null)
    visibilityMutation.mutate({
      id: change.id,
      visibility: change.nextVisibility,
      ifMatch: change.ifMatch,
      reason,
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
