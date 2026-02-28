import { useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import {
  DOCUMENT_UPLOAD_ACCEPTED_FILE_TYPES,
  documentsUseCases,
  validateDocumentUploadFile,
} from '@/features/documents'
import { queryKeys } from '@/lib/queryKeys'

export const ACCEPTED_FILE_TYPES = DOCUMENT_UPLOAD_ACCEPTED_FILE_TYPES

export function useUploadDocumentFlow({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('')
  const [releaseBranch, setReleaseBranch] = useState('')
  const [tags, setTags] = useState('')
  const [error, setError] = useState('')
  const [dragActive, setDragActive] = useState(false)

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      documentsUseCases.uploadDocument(file, {
        title,
        description,
        category,
        releaseBranch,
        tags,
      }),
    onSuccess: (doc) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all })
      onClose()
      navigate(`/documents/${doc.id}/fullscreen`)
    },
    onError: (err: unknown) => {
      const apiError = err as { response?: { data?: { detail?: string } } }
      setError(apiError.response?.data?.detail || 'Failed to upload document')
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
    if (!selectedFile) {
      setError('Please select a file to upload')
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
    error,
    setError,
    dragActive,
    setDragActive,
    uploadMutation,
    handleFileSelect,
    handleDrop,
    handleSubmit,
  }
}
