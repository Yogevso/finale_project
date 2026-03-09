import { useCallback, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import {
  documentsUseCases,
  getDefaultAudienceForRole,
  getAudienceDirtyState,
  validateAudienceFormPayload,
  type DocumentCreateFormData,
} from '@/features/documents'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { queryKeys } from '@/lib/queryKeys'
import { extractApiErrorMessage, useToast } from '@/lib/toast'

export function useCreateDocumentFlow({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { user } = useAuth()
  const toast = useToast()
  const defaultVisibility = getDefaultAudienceForRole(user?.role)
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null)

  const [formData, setFormData] = useState<DocumentCreateFormData>({
    title: '',
    description: '',
    status: 'draft',
    visibility: defaultVisibility,
    company_ids: [],
    category: '',
    release_branch: '',
    tags: '',
    due_date: '',
    content: '',
  })
  const [error, setError] = useState('')
  const [generateWord, setGenerateWord] = useState(false)
  const debouncedTitle = useDebouncedValue(formData.title, 250)
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
    (formData.due_date?.trim() ?? '') !== '' ||
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
      toast.success('Document created', 'Opening the editor...')
      onClose()
      navigate(`/documents/${doc.id}/fullscreen`)
    },
    onError: (err: unknown) => {
      const message = extractApiErrorMessage(err, 'Failed to create document')
      setError(message)
      toast.error('Failed to create document', message)
    },
  })

  const duplicateCheckQuery = useQuery({
    queryKey: queryKeys.documents.duplicateCheck(debouncedTitle.trim()),
    queryFn: () => api.checkDocumentDuplicates(debouncedTitle.trim()),
    enabled: debouncedTitle.trim().length >= 3,
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
    selectedTemplateId,
    setSelectedTemplateId,
    createMutation,
    duplicateCheckQuery,
    audienceDirtyState,
    handleSubmit,
    hasUnsavedChanges,
    confirmClose,
  }
}
