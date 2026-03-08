import { useCallback, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
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
import type { DocumentVisibility } from '@/types'
import { queryKeys } from '@/lib/queryKeys'
import { extractApiErrorMessage, useToast } from '@/lib/toast'

export const ACCEPTED_FILE_TYPES = DOCUMENT_UPLOAD_ACCEPTED_FILE_TYPES

export function useUploadDocumentFlow({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { user } = useAuth()
  const toast = useToast()
  const defaultVisibility = getDefaultAudienceForRole(user?.role)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('')
  const [releaseBranch, setReleaseBranch] = useState('')
  const [tags, setTags] = useState('')
  const [visibility, setVisibility] = useState<DocumentVisibility>(defaultVisibility)
  const [companyIds, setCompanyIds] = useState<number[]>([])
  const [error, setError] = useState('')
  const [dragActive, setDragActive] = useState(false)
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
    releaseBranch.trim() !== '' ||
    tags.trim() !== '' ||
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

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      documentsUseCases.uploadDocument(file, {
        title,
        description,
        category,
        releaseBranch,
        tags,
        visibility,
        companyIds,
      }),
    onSuccess: (doc) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all })
      toast.success('Document uploaded', 'Opening the document...')
      onClose()
      navigate(`/documents/${doc.id}/fullscreen`)
    },
    onError: (err: unknown) => {
      const message = extractApiErrorMessage(err, 'Failed to upload document')
      setError(message)
      toast.error('Upload failed', message)
    },
  })

  const handleFileSelect = (file: File) => {
    const validationError = validateDocumentUploadFile(file)
    if (validationError) {
      setError(validationError)
      return
    }

    setSelectedFile(file)
    setError('')
    if (!title) {
      setTitle(file.name.replace(/\.[^/.]+$/, ''))
    }
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
    releaseBranch,
    setReleaseBranch,
    tags,
    setTags,
    visibility,
    setVisibility,
    companyIds,
    setCompanyIds,
    error,
    setError,
    dragActive,
    setDragActive,
    audienceDirtyState,
    uploadMutation,
    handleFileSelect,
    handleDrop,
    handleSubmit,
    hasUnsavedChanges,
    confirmClose,
  }
}
