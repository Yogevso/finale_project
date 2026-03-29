import { useCallback, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import {
  DOCUMENT_UPLOAD_ACCEPTED_FILE_TYPES,
  documentsUseCases,
  getDefaultAudienceForRole,
  getAudienceDirtyState,
  validateAudienceFormPayload,
  validateDocumentUploadFile,
} from '@/features/documents'
import { useAuth } from '@/lib/auth'
import type { DocumentStatus, DocumentVisibility } from '@/types'
import { queryKeys } from '@/lib/queryKeys'
import { extractApiErrorMessage, useToast } from '@/lib/toast'
import {
  DOCUMENT_INPUT_LIMITS,
  normalizeCommaSeparatedInput,
  normalizeFileStem,
  normalizeMultilineInput,
  normalizeSingleLineInput,
} from '@/lib/uiInputRules'

export const ACCEPTED_FILE_TYPES = DOCUMENT_UPLOAD_ACCEPTED_FILE_TYPES
export const MANAGER_UPLOAD_STATUS_OPTIONS: Array<{ value: DocumentStatus; label: string }> = [
  { value: 'draft', label: 'Draft' },
  { value: 'pending_review', label: 'Pending Review' },
  { value: 'approved', label: 'Approved' },
  { value: 'active', label: 'Active' },
]

type SupplementalUploadSlot = 'content' | 'releaseNotes'

export function useUploadDocumentFlow({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { user, isManager } = useAuth()
  const toast = useToast()
  const defaultVisibility = getDefaultAudienceForRole(user?.role)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('')
  const [platform, setPlatform] = useState('')
  const [releaseBranch, setReleaseBranch] = useState('')
  const [tags, setTags] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [uploadStatus, setUploadStatus] = useState<DocumentStatus>('draft')
  const [visibility, setVisibility] = useState<DocumentVisibility>(defaultVisibility)
  const [companyIds, setCompanyIds] = useState<number[]>([])
  const [contentFile, setContentFile] = useState<File | null>(null)
  const [releaseNotesFile, setReleaseNotesFile] = useState<File | null>(null)
  const [pdfConversionTarget, setPdfConversionTarget] = useState<'docx' | 'pptx'>('docx')
  const [error, setError] = useState('')
  const [dragActive, setDragActive] = useState(false)
  const [uploadProgressPercent, setUploadProgressPercent] = useState<number | null>(null)
  const selectedFileIsPdf = useMemo(() => {
    if (!selectedFile) {
      return false
    }
    const normalizedType = (selectedFile.type || '').toLowerCase()
    const normalizedName = (selectedFile.name || '').toLowerCase()
    return normalizedType === 'application/pdf' || normalizedName.endsWith('.pdf')
  }, [selectedFile])
  const audienceDirtyState = getAudienceDirtyState(
    {
      visibility: defaultVisibility,
      company_ids: [],
    },
    {
      visibility,
      company_ids: companyIds,
    },
  )

  // Check if form has any unsaved changes
  const hasUnsavedChanges =
    selectedFile !== null ||
    title.trim() !== '' ||
    description.trim() !== '' ||
    category.trim() !== '' ||
    platform.trim() !== '' ||
    releaseBranch.trim() !== '' ||
    tags.trim() !== '' ||
    dueDate.trim() !== '' ||
    contentFile !== null ||
    releaseNotesFile !== null ||
    (isManager && uploadStatus !== 'draft') ||
    audienceDirtyState.visibilityChanged ||
    audienceDirtyState.companyAssignmentsChanged

  const platformSuggestionsQuery = useQuery({
    queryKey: queryKeys.documents.list({ page: 1, page_size: 100 }),
    queryFn: () =>
      documentsUseCases.listDocuments({
        page: 1,
        page_size: 100,
      }),
    staleTime: 60_000,
  })

  const platformSuggestions = useMemo(() => {
    const names = (platformSuggestionsQuery.data?.items ?? [])
      .map((document) => document.platform?.trim())
      .filter((platformName): platformName is string => Boolean(platformName))

    return Array.from(new Set(names)).sort((left, right) => left.localeCompare(right))
  }, [platformSuggestionsQuery.data?.items])
  const normalizedUploadMetadata = {
    title:
      normalizeSingleLineInput(title, DOCUMENT_INPUT_LIMITS.title) ||
      normalizeFileStem(selectedFile?.name, DOCUMENT_INPUT_LIMITS.title),
    description: normalizeMultilineInput(description, DOCUMENT_INPUT_LIMITS.description),
    category: normalizeSingleLineInput(category, DOCUMENT_INPUT_LIMITS.category),
    platform: normalizeSingleLineInput(platform, DOCUMENT_INPUT_LIMITS.platform),
    releaseBranch: normalizeSingleLineInput(releaseBranch, DOCUMENT_INPUT_LIMITS.releaseBranch),
    tags: normalizeCommaSeparatedInput(tags, DOCUMENT_INPUT_LIMITS.tags),
    dueDate: dueDate.trim(),
  }

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      documentsUseCases.uploadDocument(file, {
        ...normalizedUploadMetadata,
        status: isManager ? uploadStatus : undefined,
        visibility,
        companyIds,
        contentFile,
        releaseNotesFile,
        pdfConversionTarget: selectedFileIsPdf ? pdfConversionTarget : undefined,
      }, {
        onUploadProgress: (event) => {
          if (!event.total || event.total <= 0) {
            return
          }
          setUploadProgressPercent(
            Math.max(0, Math.min(100, Math.round((event.loaded / event.total) * 100))),
          )
        },
      }),
    onMutate: () => {
      setUploadProgressPercent(0)
    },
    onSuccess: (doc) => {
      setUploadProgressPercent(100)
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all })
      toast.success('Document uploaded', 'Opening the document...')
      onClose()
      navigate(`/documents/${doc.id}/fullscreen`)
    },
    onError: (err: unknown) => {
      setUploadProgressPercent(null)
      const message = extractApiErrorMessage(err, 'Failed to upload document')
      setError(message)
      toast.error('Upload failed', message)
    },
  })

  const confirmClose = useCallback(() => {
    if (!hasUnsavedChanges) {
      onClose()
      return
    }
    if (confirm('You have unsaved changes. Discard them?')) {
      onClose()
    }
  }, [hasUnsavedChanges, onClose])

  const handleFileSelect = (file: File) => {
    const validationError = validateDocumentUploadFile(file)
    if (validationError) {
      setError(validationError)
      return
    }

    setSelectedFile(file)
    setError('')
    if (!title) {
      setTitle(normalizeFileStem(file.name, DOCUMENT_INPUT_LIMITS.title))
    }
  }

  const handleSupplementalFileSelect = (slot: SupplementalUploadSlot, file: File | null) => {
    if (file === null) {
      if (slot === 'content') {
        setContentFile(null)
      } else {
        setReleaseNotesFile(null)
      }
      return
    }

    const validationError = validateDocumentUploadFile(file)
    if (validationError) {
      const label = slot === 'content' ? 'Content file' : 'Release notes file'
      setError(`${label}: ${validationError}`)
      return
    }

    if (slot === 'content') {
      setContentFile(file)
    } else {
      setReleaseNotesFile(file)
    }
    setError('')
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
    if (e.dataTransfer.files?.[0]) {
      handleFileSelect(e.dataTransfer.files[0])
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!selectedFile) {
      setError('Please select a file to upload')
      return
    }

    if (!normalizedUploadMetadata.platform) {
      setError('Platform is required')
      return
    }

    const audienceValidationIssue = validateAudienceFormPayload({
      visibility,
      company_ids: companyIds,
    })
    if (audienceValidationIssue) {
      setError(audienceValidationIssue.message)
      return
    }

    uploadMutation.mutate(selectedFile)
  }

  return {
    fileInputRef,
    selectedFile,
    setSelectedFile,
    title,
    setTitle,
    description,
    setDescription,
    category,
    setCategory,
    platform,
    setPlatform,
    platformSuggestions,
    releaseBranch,
    setReleaseBranch,
    tags,
    setTags,
    dueDate,
    setDueDate,
    uploadStatus,
    setUploadStatus,
    visibility,
    setVisibility,
    companyIds,
    setCompanyIds,
    canManageAdvancedUploadOptions: isManager,
    contentFile,
    releaseNotesFile,
    selectedFileIsPdf,
    pdfConversionTarget,
    setPdfConversionTarget,
    error,
    setError,
    dragActive,
    setDragActive,
    uploadProgressPercent,
    audienceDirtyState,
    uploadMutation,
    handleFileSelect,
    handleSupplementalFileSelect,
    handleDrop,
    handleSubmit,
    hasUnsavedChanges,
    confirmClose,
  }
}
