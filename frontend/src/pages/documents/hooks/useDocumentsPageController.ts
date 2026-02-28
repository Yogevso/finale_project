import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'

import {
  buildDocumentsListQueryParams,
  documentsUseCases,
} from '@/features/documents'
import { useAuth } from '@/lib/auth'
import { queryKeys } from '@/lib/queryKeys'
import type { DocumentStatus, DocumentVisibility } from '@/types'

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
    }: {
      id: number
      visibility: DocumentVisibility
      ifMatch: string
    }) => documentsUseCases.updateVisibility(id, visibility, ifMatch),
    onSuccess: (_, variables) => {
      setVisibilityOverrides((prev) => {
        const next = { ...prev }
        delete next[variables.id]
        return next
      })
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all })
    },
    onError: (error: unknown, variables) => {
      const apiError = error as { response?: { data?: { detail?: string } }; message?: string }
      setVisibilityOverrides((prev) => {
        const next = { ...prev }
        delete next[variables.id]
        return next
      })
      alert(apiError.response?.data?.detail || apiError.message || 'Failed to update visibility.')
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

  const handleVisibilityChange = (id: number, visibility: DocumentVisibility, ifMatch: string) => {
    setVisibilityOverrides((prev) => ({ ...prev, [id]: visibility }))
    visibilityMutation.mutate({ id, visibility, ifMatch })
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
    isQuickCreateMode,
    documentsQuery,
    deleteMutation,
    visibilityMutation,
    handleDelete,
    handleVisibilityChange,
  }
}
