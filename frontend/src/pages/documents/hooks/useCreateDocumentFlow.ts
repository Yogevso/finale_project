import { useCallback, useMemo, useState } from 'react'
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
import { createCustomDocumentTemplate } from '@/lib/documentTemplates'
import { queryKeys } from '@/lib/queryKeys'
import { extractApiErrorMessage, useToast } from '@/lib/toast'
import type { DocumentListResponse } from '@/types'

type SourceDocumentSummary = Pick<DocumentListResponse['items'][number], 'id' | 'title' | 'document_number'>

export function useCreateDocumentFlow({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { user } = useAuth()
  const toast = useToast()
  const defaultVisibility = getDefaultAudienceForRole(user?.role)
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null)
  const [saveAsTemplate, setSaveAsTemplate] = useState(false)
  const [templateName, setTemplateName] = useState('')
  const [templateDescription, setTemplateDescription] = useState('')
  const [copySourceSearch, setCopySourceSearch] = useState('')
  const [selectedSourceDocument, setSelectedSourceDocument] = useState<SourceDocumentSummary | null>(
    null,
  )

  const [formData, setFormData] = useState<DocumentCreateFormData>({
    title: '',
    description: '',
    status: 'draft',
    visibility: defaultVisibility,
    company_ids: [],
    category: '',
    topic: '',
    platform: '',
    release_branch: '',
    tags: '',
    due_date: '',
    content: '',
  })
  const [error, setError] = useState('')
  const [generateWord, setGenerateWord] = useState(false)
  const debouncedTitle = useDebouncedValue(formData.title, 250)
  const debouncedCopySourceSearch = useDebouncedValue(copySourceSearch, 250)
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
    (formData.topic?.trim() ?? '') !== '' ||
    (formData.platform?.trim() ?? '') !== '' ||
    (formData.release_branch?.trim() ?? '') !== '' ||
    (formData.tags?.trim() ?? '') !== '' ||
    (formData.due_date?.trim() ?? '') !== '' ||
    saveAsTemplate ||
    templateName.trim() !== '' ||
    templateDescription.trim() !== '' ||
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
    enabled: !saveAsTemplate && debouncedTitle.trim().length >= 3,
  })

  const copySourceResultsQuery = useQuery({
    queryKey: queryKeys.documents.list({
      page: 1,
      page_size: 8,
      search: debouncedCopySourceSearch.trim(),
    }),
    queryFn: () =>
      documentsUseCases.listDocuments({
        page: 1,
        page_size: 8,
        search: debouncedCopySourceSearch.trim(),
      }),
    enabled: !saveAsTemplate && debouncedCopySourceSearch.trim().length >= 2,
  })

  const platformSuggestionsQuery = useQuery({
    queryKey: queryKeys.documents.list({ page: 1, page_size: 100 }),
    queryFn: () =>
      documentsUseCases.listDocuments({
        page: 1,
        page_size: 100,
      }),
    enabled: !saveAsTemplate,
    staleTime: 60_000,
  })

  const platformSuggestions = useMemo(() => {
    const names = (platformSuggestionsQuery.data?.items ?? [])
      .map((document) => document.platform?.trim())
      .filter((platformName): platformName is string => Boolean(platformName))

    return Array.from(new Set(names)).sort((left, right) => left.localeCompare(right))
  }, [platformSuggestionsQuery.data?.items])

  const copySourceMutation = useMutation({
    mutationFn: (documentId: number) => documentsUseCases.loadDuplicateDocumentDraft(documentId),
    onSuccess: (draft, documentId) => {
      const matchedSourceDocument =
        copySourceResultsQuery.data?.items.find((document) => document.id === documentId) || null

      setFormData((previous) => ({
        ...previous,
        ...draft,
      }))
      setSelectedTemplateId(null)
      setSelectedSourceDocument(
        matchedSourceDocument
          ? {
              id: matchedSourceDocument.id,
              title: matchedSourceDocument.title,
              document_number: matchedSourceDocument.document_number,
            }
          : {
              id: documentId,
              title: draft.title.replace(/^Copy of\s+/i, ''),
              document_number: '',
            },
      )
      setCopySourceSearch('')
      setError('')
    },
    onError: (err: unknown) => {
      const message = extractApiErrorMessage(err, 'Failed to load source document')
      setError(message)
      toast.error('Failed to copy document', message)
    },
  })

  const handleCopyFromDocument = async (document: SourceDocumentSummary) => {
    await copySourceMutation.mutateAsync(document.id)
    setSelectedSourceDocument(document)
  }

  const clearCopiedSource = () => {
    setSelectedSourceDocument(null)
    setCopySourceSearch('')
    setFormData((previous) => ({
      ...previous,
      parent_id: undefined,
    }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!formData.title.trim()) {
      setError('Title is required')
      return
    }

    if (!saveAsTemplate && !formData.platform?.trim() && !formData.platform_id) {
      setError('Platform is required')
      return
    }

    if (saveAsTemplate && !(templateName.trim() || formData.title.trim())) {
      setError('Add a template name before saving to the Template Library')
      return
    }

    if (saveAsTemplate) {
      createCustomDocumentTemplate({
        name: templateName.trim() || formData.title.trim(),
        description:
          templateDescription.trim() ||
          formData.description?.trim() ||
          'Reusable template saved from the document editor.',
        category: formData.category?.trim() || 'Custom',
        tags: (formData.tags || '')
          .split(',')
          .map((tag) => tag.trim())
          .filter(Boolean),
        content: formData.content?.trim() || '<p>Start writing here.</p>',
      })
      toast.success('Template saved', 'Added to your personal Template Library.')
      onClose()
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
    saveAsTemplate,
    setSaveAsTemplate,
    templateName,
    setTemplateName,
    templateDescription,
    setTemplateDescription,
    copySourceSearch,
    setCopySourceSearch,
    selectedSourceDocument,
    copySourceResultsQuery,
    copySourceMutation,
    handleCopyFromDocument,
    clearCopiedSource,
    platformSuggestions,
    createMutation,
    duplicateCheckQuery,
    audienceDirtyState,
    handleSubmit,
    hasUnsavedChanges,
    confirmClose,
  }
}
