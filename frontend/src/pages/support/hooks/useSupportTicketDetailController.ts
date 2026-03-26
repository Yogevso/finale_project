import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ATTACHMENT_INPUT_ACCEPT, validateAttachmentFile } from '@/lib/attachmentUpload'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { extractApiErrorMessage, useToast } from '@/lib/toast'
import type {
  SupportTicketDetail,
  SupportTicketPriority,
  SupportTicketStatus,
} from '@/types/chat'

export function useSupportTicketDetailController(
  ticket: SupportTicketDetail,
) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const toast = useToast()
  const [message, setMessage] = useState('')
  const [messageError, setMessageError] = useState('')
  const [isInternal, setIsInternal] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [showAssign, setShowAssign] = useState(false)
  const [showHandoff, setShowHandoff] = useState(false)
  const [showCanned, setShowCanned] = useState(false)
  const [cannedSearch, setCannedSearch] = useState('')
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const canSend = Boolean(message.trim() || selectedFile)

  const viewersQuery = useQuery({
    queryKey: ['ticketViewers', ticket.id],
    queryFn: () => api.getTicketViewers(ticket.id),
    refetchInterval: 15000,
  })
  const viewerIds = viewersQuery.data?.viewer_ids ?? []
  const otherViewers = viewerIds.filter((id) => id !== user?.id)

  const invalidateTicketQueries = () => {
    queryClient.invalidateQueries({ queryKey: ['supportTicket', ticket.id] })
    queryClient.invalidateQueries({ queryKey: ['supportTickets'] })
  }

  const resetComposer = () => {
    setMessage('')
    setMessageError('')
    setSelectedFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const sendMutation = useMutation({
    mutationFn: (data: { content: string; is_internal_note: boolean; file: File | null }) =>
      api.sendSupportTicketMessage(ticket.id, data),
    onSuccess: () => {
      resetComposer()
      invalidateTicketQueries()
    },
    onError: (error: unknown) => {
      toast.error('Failed to send message', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: { status?: SupportTicketStatus; priority?: SupportTicketPriority }) =>
      api.updateSupportTicket(ticket.id, data),
    onSuccess: invalidateTicketQueries,
    onError: (error: unknown) => {
      toast.error('Failed to update ticket', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  const unassignMutation = useMutation({
    mutationFn: (agentId: number) => api.unassignSupportAgent(ticket.id, agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['supportTicket', ticket.id] })
    },
    onError: (error: unknown) => {
      toast.error('Failed to unassign agent', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  const cannedQuery = useQuery({
    queryKey: ['cannedResponses', cannedSearch],
    queryFn: () => api.getCannedResponses({ search: cannedSearch || undefined }),
    enabled: showCanned,
  })

  const handleSend = () => {
    if (!canSend) {
      setMessageError('A reply message or attachment is required.')
      return
    }

    sendMutation.mutate({
      content: message.trim(),
      is_internal_note: isInternal,
      file: selectedFile,
    })
  }

  const insertCanned = (content: string) => {
    const resolved = content
      .replace(/\{\{customer_name\}\}/g, ticket.customer_full_name || 'Customer')
      .replace(/\{\{ticket_id\}\}/g, String(ticket.id))
      .replace(/\{\{agent_name\}\}/g, user?.full_name || 'Agent')
    setMessage((previous) => (previous ? `${previous}\n${resolved}` : resolved))
    setMessageError('')
    setShowCanned(false)
    setCannedSearch('')
  }

  const handleSelectedFile = (file: File | null) => {
    if (!file) {
      setSelectedFile(null)
      return
    }

    const validationError = validateAttachmentFile(file)
    if (validationError) {
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      toast.error('Attachment rejected', validationError)
      return
    }

    setSelectedFile(file)
    if (messageError) {
      setMessageError('')
    }
  }

  const removeSelectedFile = () => {
    setSelectedFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return {
    attachmentInputAccept: ATTACHMENT_INPUT_ACCEPT,
    canSend,
    cannedQuery,
    cannedSearch,
    fileInputRef,
    handleSelectedFile,
    handleSend,
    insertCanned,
    isInternal,
    message,
    messageError,
    otherViewers,
    removeSelectedFile,
    selectedFile,
    sendMutation,
    setCannedSearch,
    setIsInternal,
    setMessage,
    setMessageError,
    setShowAssign,
    setShowCanned,
    setShowHandoff,
    showAssign,
    showCanned,
    showHandoff,
    ticket,
    unassignMutation,
    updateMutation,
    user,
  }
}
