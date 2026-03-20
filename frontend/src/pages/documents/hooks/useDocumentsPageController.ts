import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'

import { api } from '@/lib/api'
import {
  buildDocumentsListQueryParams,
  documentsUseCases,
} from '@/features/documents'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { useAuth } from '@/lib/auth'
import { queryKeys } from '@/lib/queryKeys'
import { buildSavedViewPayload, parseSavedDocumentsView } from '@/pages/documents/lib/savedViews'
import { extractApiErrorMessage, useToast } from '@/lib/toast'
import type { BulkDocumentMetadataUpdate, DocumentStatus, DocumentVisibility } from '@/types'

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
  const toast = useToast()

  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search, 300)
  const [statusFilter, setStatusFilter] = useState<DocumentStatus | ''>('')
  const [visibilityFilter, setVisibilityFilter] = useState<DocumentVisibility | ''>('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [companyIdFilter, setCompanyIdFilter] = useState<number | null>(null)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [activeSavedViewId, setActiveSavedViewId] = useState<number | null>(null)
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<number[]>([])
  const [showBulkEditModal, setShowBulkEditModal] = useState(false)
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
    categoryFilter,
    companyIdFilter,
    dateFrom,
    dateTo,
  })

  const documentsQuery = useQuery({
    queryKey: queryKeys.documents.list(listQueryParams),
    queryFn: () => documentsUseCases.listDocuments(listQueryParams),
  })

  const companiesQuery = useQuery({
    queryKey: ['companies', 'documents-filter'],
    queryFn: () => api.getCompanies({ page: 1, per_page: 100 }),
    enabled: isManager,
  })

  const savedViewsQuery = useQuery({
    queryKey: ['documents', 'saved-views'],
    queryFn: () => api.getSavedSearches(),
  })

  const savedViews = useMemo(
    () => (savedViewsQuery.data ?? []).map(parseSavedDocumentsView),
    [savedViewsQuery.data],
  )

  useEffect(() => {
    const currentItems = documentsQuery.data?.items
    if (!currentItems) {
      return
    }

    const currentPageIds = new Set(currentItems.map((document) => document.id))
    setSelectedDocumentIds((previous) => previous.filter((documentId) => currentPageIds.has(documentId)))
  }, [documentsQuery.data?.items])

  const deleteMutation = useMutation({
    mutationFn: (id: number) => documentsUseCases.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all })
    },
    onError: (error: unknown) => {
      const apiError = error as { response?: { data?: { detail?: string } }; message?: string }
      alert(
        apiError.response?.data?.detail ||
          apiError.message ||
          'Failed to delete document. You may need Manager or Admin role.',
      )
    },
  })

  const archiveMutation = useMutation({
    mutationFn: (id: number) => documentsUseCases.archiveDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all })
    },
    onError: (error: unknown) => {
      const apiError = error as { response?: { data?: { detail?: string } }; message?: string }
      alert(apiError.response?.data?.detail || apiError.message || 'Failed to archive document.')
    },
  })

  const restoreMutation = useMutation({
    mutationFn: (id: number) => documentsUseCases.restoreDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all })
    },
    onError: (error: unknown) => {
      const apiError = error as { response?: { data?: { detail?: string } }; message?: string }
      alert(apiError.response?.data?.detail || apiError.message || 'Failed to restore document.')
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
      setVisibilityOverrides((previous) => {
        const nextOverrides = { ...previous }
        delete nextOverrides[variables.id]
        return nextOverrides
      })
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all })
    },
    onError: (error: unknown, variables) => {
      setVisibilityOverrides((previous) => {
        const nextOverrides = { ...previous }
        delete nextOverrides[variables.id]
        return nextOverrides
      })
      alert(getVisibilityUpdateErrorMessage(error))
    },
  })

  const bulkMetadataMutation = useMutation({
    mutationFn: (payload: BulkDocumentMetadataUpdate) => api.bulkUpdateDocumentMetadata(payload),
    onSuccess: () => {
      setShowBulkEditModal(false)
      setSelectedDocumentIds([])
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all })
      toast.success('Metadata updated')
    },
    onError: (error: unknown) => {
      toast.error('Failed to update metadata', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  const saveViewMutation = useMutation({
    mutationFn: (name: string) =>
      api.createSavedSearch({
        name,
        ...buildSavedViewPayload({
          search,
          statusFilter,
          visibilityFilter,
          categoryFilter,
          companyIdFilter,
          dateFrom,
          dateTo,
        }),
      }),
    onSuccess: (savedView) => {
      setActiveSavedViewId(savedView.id)
      queryClient.invalidateQueries({ queryKey: ['documents', 'saved-views'] })
    },
    onError: (error: unknown) => {
      const apiError = error as { response?: { data?: { detail?: string } }; message?: string }
      alert(apiError.response?.data?.detail || apiError.message || 'Failed to save this view.')
    },
  })

  const deleteViewMutation = useMutation({
    mutationFn: (savedViewId: number) => api.deleteSavedSearch(savedViewId),
    onSuccess: (_, savedViewId) => {
      if (activeSavedViewId === savedViewId) {
        setActiveSavedViewId(null)
      }
      queryClient.invalidateQueries({ queryKey: ['documents', 'saved-views'] })
    },
    onError: (error: unknown) => {
      const apiError = error as { response?: { data?: { detail?: string } }; message?: string }
      alert(apiError.response?.data?.detail || apiError.message || 'Failed to delete this view.')
    },
  })

  const clearActiveSavedView = () => {
    setActiveSavedViewId(null)
    setPage(1)
  }

  const handleDelete = (id: number, title: string) => {
    if (!isManager) {
      return
    }
    if (confirm(`Are you sure you want to delete "${title}"?`)) {
      deleteMutation.mutate(id)
    }
  }

  const handleArchiveOrRestore = (
    id: number,
    title: string,
    currentStatus: DocumentStatus,
  ) => {
    if (!isManager) {
      return
    }

    if (currentStatus === 'archived') {
      restoreMutation.mutate(id)
      return
    }

    if (confirm(`Archive "${title}"? You can restore it later from the archived view.`)) {
      archiveMutation.mutate(id)
    }
  }

  const handleVisibilityChange = (change: VisibilityChangeRequest) => {
    if (change.currentVisibility === change.nextVisibility) {
      setVisibilityOverrides((previous) => {
        const nextOverrides = { ...previous }
        delete nextOverrides[change.id]
        return nextOverrides
      })
      return
    }

    setVisibilityOverrides((previous) => ({ ...previous, [change.id]: change.nextVisibility }))
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
    setVisibilityOverrides((previous) => {
      const nextOverrides = { ...previous }
      delete nextOverrides[pendingId]
      return nextOverrides
    })
  }

  const resetFilters = () => {
    setSearch('')
    setStatusFilter('')
    setVisibilityFilter('')
    setCategoryFilter('')
    setCompanyIdFilter(null)
    setDateFrom('')
    setDateTo('')
    setActiveSavedViewId(null)
    setPage(1)
  }

  const applySavedView = (savedViewId: number) => {
    const targetView = savedViews.find((savedView) => savedView.id === savedViewId)
    if (!targetView) {
      return
    }
    setSearch(targetView.filters.search)
    setStatusFilter(targetView.filters.statusFilter)
    setVisibilityFilter(targetView.filters.visibilityFilter)
    setCategoryFilter(targetView.filters.categoryFilter)
    setCompanyIdFilter(targetView.filters.companyIdFilter)
    setDateFrom(targetView.filters.dateFrom)
    setDateTo(targetView.filters.dateTo)
    setActiveSavedViewId(savedViewId)
    setPage(1)
  }

  const toggleDocumentSelection = (documentId: number) => {
    setSelectedDocumentIds((previous) =>
      previous.includes(documentId)
        ? previous.filter((value) => value !== documentId)
        : [...previous, documentId],
    )
  }

  const toggleAllVisibleDocuments = () => {
    const currentPageIds = (documentsQuery.data?.items ?? []).map((document) => document.id)
    if (currentPageIds.length === 0) {
      return
    }
    const areAllSelected = currentPageIds.every((documentId) => selectedDocumentIds.includes(documentId))
    if (areAllSelected) {
      setSelectedDocumentIds((previous) =>
        previous.filter((documentId) => !currentPageIds.includes(documentId)),
      )
      return
    }
    setSelectedDocumentIds((previous) => Array.from(new Set([...previous, ...currentPageIds])))
  }

  return {
    isEditor,
    isManager,
    page,
    setPage,
    search,
    setSearch: (value: string) => {
      clearActiveSavedView()
      setSearch(value)
    },
    statusFilter,
    setStatusFilter: (value: DocumentStatus | '') => {
      clearActiveSavedView()
      setStatusFilter(value)
    },
    visibilityFilter,
    setVisibilityFilter: (value: DocumentVisibility | '') => {
      clearActiveSavedView()
      setVisibilityFilter(value)
    },
    categoryFilter,
    setCategoryFilter: (value: string) => {
      clearActiveSavedView()
      setCategoryFilter(value)
    },
    companyIdFilter,
    setCompanyIdFilter: (value: number | null) => {
      clearActiveSavedView()
      setCompanyIdFilter(value)
    },
    dateFrom,
    setDateFrom: (value: string) => {
      clearActiveSavedView()
      setDateFrom(value)
    },
    dateTo,
    setDateTo: (value: string) => {
      clearActiveSavedView()
      setDateTo(value)
    },
    activeSavedViewId,
    savedViews,
    saveCurrentView: (name: string) => saveViewMutation.mutate(name),
    isSavingCurrentView: saveViewMutation.isPending,
    deleteSavedView: (savedViewId: number) => deleteViewMutation.mutate(savedViewId),
    isDeletingSavedView: deleteViewMutation.isPending,
    applySavedView,
    resetFilters,
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
    companiesQuery,
    deleteMutation,
    archiveMutation,
    visibilityMutation,
    bulkMetadataMutation,
    restoreMutation,
    showBulkEditModal,
    setShowBulkEditModal,
    selectedDocumentIds,
    toggleDocumentSelection,
    toggleAllVisibleDocuments,
    clearSelection: () => setSelectedDocumentIds([]),
    handleArchiveOrRestore,
    handleDelete,
    handleVisibilityChange,
    confirmPendingVisibilityChange,
    cancelPendingVisibilityChange,
  }
}
