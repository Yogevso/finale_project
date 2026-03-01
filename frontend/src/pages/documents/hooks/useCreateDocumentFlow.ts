import { useCallback, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import {
  documentsUseCases,
  getDefaultAudienceForRole,
  getAudienceDirtyState,
  validateAudienceFormPayload,
  type DocumentCreateFormData,
} from '@/features/documents'
import { useAuth } from '@/lib/auth'
import { queryKeys } from '@/lib/queryKeys'

export function useCreateDocumentFlow({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { user } = useAuth()
  const defaultVisibility = getDefaultAudienceForRole(user?.role)

  const [formData, setFormData] = useState<DocumentCreateFormData>({
    title: '',
    description: '',
    status: 'draft',
    visibility: defaultVisibility,
    company_ids: [],
    category: '',
    release_branch: '',
    tags: '',
    content: '',
  })
  const [error, setError] = useState('')
  const [generateWord, setGenerateWord] = useState(false)
  const audienceDirtyState = getAudienceDirtyState(
    {
      visibility: defaultVisibility,
      company_ids: [],
    },
    {
      visibility: formData.visibility,
      company_ids: formData.company_ids,
    },
  )

  // Check if form has any unsaved changes
  const hasUnsavedChanges =
    formData.title.trim() !== '' ||
    (formData.description?.trim() ?? '') !== '' ||
    (formData.content?.trim() ?? '') !== '' ||
    (formData.category?.trim() ?? '') !== '' ||
    (formData.release_branch?.trim() ?? '') !== '' ||
    (formData.tags?.trim() ?? '') !== '' ||
    audienceDirtyState.visibilityChanged ||
    audienceDirtyState.companyAssignmentsChanged

  const confirmClose = useCallback(() => {
    if (!hasUnsavedChanges) {
      onClose()
      return
    }
    if (confirm('You have unsaved changes. Discard them?')) {
      onClose()
    }
  }, [hasUnsavedChanges, onClose])

  const createMutation = useMutation({
    mutationFn: (data: DocumentCreateFormData) =>
      documentsUseCases.createDraftDocument(data, { generateWord }),
    onSuccess: (doc) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all })
      onClose()
      navigate(`/documents/${doc.id}/fullscreen`)
    },
    onError: (err: unknown) => {
      const apiError = err as { response?: { data?: { detail?: string } }; message?: string }
      setError(apiError.response?.data?.detail || apiError.message || 'Failed to create document')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!formData.title.trim()) {
      setError('Title is required')
      return
    }

    const audienceValidationIssue = validateAudienceFormPayload(formData)
    if (audienceValidationIssue) {
      setError(audienceValidationIssue.message)
      return
    }

    createMutation.mutate(formData)
  }

  return {
    formData,
    setFormData,
    error,
    setError,
    generateWord,
    setGenerateWord,
    createMutation,
    audienceDirtyState,
    handleSubmit,
    hasUnsavedChanges,
    confirmClose,
  }
}
