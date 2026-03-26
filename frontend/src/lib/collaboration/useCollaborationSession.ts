import { useCallback, useEffect, useRef } from 'react'
import { reportRuntimeError, reportRuntimeWarning } from '@/lib/runtimeReporter'

interface SessionPatch {
  documentTitle?: string
  isConnected?: boolean
  isSynced?: boolean
}

interface UseCollaborationSessionOptions {
  documentId: number
  documentTitle: string
  autoSaveInterval: number
  isConnected: boolean
  canEdit: boolean
  setSession: (documentId: number, patch: SessionPatch) => void
  startCollaborationSession: (documentId: number) => Promise<{ session_id: string }>
  endCollaborationSession: (sessionId: string, editsCount: number) => Promise<void>
  createSnapshotApi: (
    documentId: number,
    options: { name?: string; session_id?: string },
  ) => Promise<unknown>
  createAutoSnapshot: (documentId: number, sessionId?: string) => Promise<unknown>
}

export function useCollaborationSession({
  documentId,
  documentTitle,
  autoSaveInterval,
  isConnected,
  canEdit,
  setSession,
  startCollaborationSession,
  endCollaborationSession,
  createSnapshotApi,
  createAutoSnapshot,
}: UseCollaborationSessionOptions) {
  const sessionIdRef = useRef<string | null>(null)
  const editsCountRef = useRef(0)
  const autoSaveIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const flushCollaborationSessionEnd = useCallback(async () => {
    if (!sessionIdRef.current) {
      return
    }

    const sessionId = sessionIdRef.current
    const editsCount = editsCountRef.current
    sessionIdRef.current = null

    try {
      await endCollaborationSession(sessionId, editsCount)
    } catch (err) {
      reportRuntimeWarning({
        scope: 'collaboration.session',
        message: 'Failed to end collaboration session',
        error: err,
      })
    }
  }, [endCollaborationSession])

  const handleProviderConnected = useCallback(() => {
    editsCountRef.current = 0
    setSession(documentId, {
      documentTitle,
      isConnected: true,
    })

    startCollaborationSession(documentId)
      .then((response) => {
        sessionIdRef.current = response.session_id
      })
      .catch((err) => {
        reportRuntimeWarning({
          scope: 'collaboration.session',
          message: 'Failed to start collaboration session',
          error: err,
          userMessage: 'Live editing session telemetry could not be initialized. Editing can continue.',
          toastTitle: 'Collaboration session degraded',
          dedupeKey: `collab-session-start:${documentId}`,
        })
      })
  }, [documentId, documentTitle, setSession, startCollaborationSession])

  const recordLocalEdit = useCallback(() => {
    editsCountRef.current += 1
  }, [])

  const resetSessionTracking = useCallback(() => {
    sessionIdRef.current = null
    editsCountRef.current = 0
  }, [])

  const createSnapshot = useCallback(
    async (name?: string) => {
      if (!sessionIdRef.current) {
        reportRuntimeWarning({
          scope: 'collaboration.snapshot',
          message: 'Cannot create snapshot without an active session',
        })
        return
      }

      try {
        await createSnapshotApi(documentId, {
          name,
          session_id: sessionIdRef.current,
        })
      } catch (error) {
        reportRuntimeError({
          scope: 'collaboration.snapshot',
          message: 'Failed to create snapshot',
          error,
          userMessage: 'Could not create a collaboration snapshot. Please try again.',
          toastTitle: 'Snapshot failed',
          dedupeKey: `collab-create-snapshot:${documentId}`,
        })
      }
    },
    [createSnapshotApi, documentId],
  )

  useEffect(() => {
    const handlePageHide = () => {
      void flushCollaborationSessionEnd()
    }

    window.addEventListener('pagehide', handlePageHide)
    return () => {
      window.removeEventListener('pagehide', handlePageHide)
    }
  }, [flushCollaborationSessionEnd])

  useEffect(() => {
    if (isConnected && autoSaveInterval > 0 && canEdit) {
      if (autoSaveIntervalRef.current) {
        clearInterval(autoSaveIntervalRef.current)
      }

      autoSaveIntervalRef.current = setInterval(async () => {
        if (sessionIdRef.current && editsCountRef.current > 0) {
          try {
            await createAutoSnapshot(documentId, sessionIdRef.current)
          } catch (error) {
            reportRuntimeWarning({
              scope: 'collaboration.snapshot',
              message: 'Auto-save snapshot failed',
              error,
              userMessage: 'Automatic snapshotting failed. Editing continues and the app will retry later.',
              toastTitle: 'Auto-save degraded',
              dedupeKey: `collab-auto-snapshot:${documentId}`,
            })
          }
        }
      }, autoSaveInterval)

      return () => {
        if (autoSaveIntervalRef.current) {
          clearInterval(autoSaveIntervalRef.current)
          autoSaveIntervalRef.current = null
        }
      }
    }

    return undefined
  }, [autoSaveInterval, canEdit, createAutoSnapshot, documentId, isConnected])

  return {
    sessionIdRef,
    flushCollaborationSessionEnd,
    handleProviderConnected,
    recordLocalEdit,
    resetSessionTracking,
    createSnapshot,
  }
}
