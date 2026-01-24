/**
 * Collaboration Store
 *
 * Global state management for real-time collaboration features.
 * Manages active sessions, collaborators, and notifications.
 */

import { create } from 'zustand'
import { CollaboratorInfo } from '@/lib/useCollaboration'

export interface CollaborationNotification {
  id: string
  type: 'join' | 'leave' | 'edit' | 'version'
  userId: string
  username: string
  message: string
  timestamp: Date
  documentId: number
}

export interface ActiveSession {
  documentId: number
  documentTitle: string
  isConnected: boolean
  isSynced: boolean
  collaborators: CollaboratorInfo[]
  startedAt: Date
}

interface CollaborationState {
  // Active collaboration sessions
  activeSessions: Map<number, ActiveSession>

  // Recent notifications (join/leave events)
  notifications: CollaborationNotification[]
  maxNotifications: number

  // Global collaborator count
  totalCollaborators: number

  // Actions
  setSession: (documentId: number, session: Partial<ActiveSession>) => void
  removeSession: (documentId: number) => void
  updateCollaborators: (documentId: number, collaborators: CollaboratorInfo[]) => void

  addNotification: (notification: Omit<CollaborationNotification, 'id' | 'timestamp'>) => void
  clearNotifications: () => void
  dismissNotification: (id: string) => void

  // Computed values
  getSession: (documentId: number) => ActiveSession | undefined
  getCollaboratorsForDocument: (documentId: number) => CollaboratorInfo[]
}

export const useCollaborationStore = create<CollaborationState>((set, get) => ({
  activeSessions: new Map(),
  notifications: [],
  maxNotifications: 50,
  totalCollaborators: 0,

  setSession: (documentId, sessionData) => {
    set((state) => {
      const newSessions = new Map(state.activeSessions)
      const existing = newSessions.get(documentId)

      newSessions.set(documentId, {
        documentId,
        documentTitle: sessionData.documentTitle || existing?.documentTitle || '',
        isConnected: sessionData.isConnected ?? existing?.isConnected ?? false,
        isSynced: sessionData.isSynced ?? existing?.isSynced ?? false,
        collaborators: sessionData.collaborators ?? existing?.collaborators ?? [],
        startedAt: existing?.startedAt || new Date(),
      })

      // Recalculate total collaborators
      let total = 0
      newSessions.forEach((session) => {
        total += session.collaborators.length
      })

      return {
        activeSessions: newSessions,
        totalCollaborators: total,
      }
    })
  },

  removeSession: (documentId) => {
    set((state) => {
      const newSessions = new Map(state.activeSessions)
      newSessions.delete(documentId)

      // Recalculate total collaborators
      let total = 0
      newSessions.forEach((session) => {
        total += session.collaborators.length
      })

      return {
        activeSessions: newSessions,
        totalCollaborators: total,
      }
    })
  },

  updateCollaborators: (documentId, collaborators) => {
    const state = get()
    const session = state.activeSessions.get(documentId)

    if (session) {
      // Detect joins and leaves
      const previousCollaborators = session.collaborators
      const previousIds = new Set(previousCollaborators.map((c) => c.userId))
      const currentIds = new Set(collaborators.map((c) => c.userId))

      // New users who joined
      collaborators.forEach((collab) => {
        if (!previousIds.has(collab.userId)) {
          state.addNotification({
            type: 'join',
            userId: collab.userId,
            username: collab.username,
            message: `${collab.username} joined the document`,
            documentId,
          })
        }
      })

      // Users who left
      previousCollaborators.forEach((collab) => {
        if (!currentIds.has(collab.userId)) {
          state.addNotification({
            type: 'leave',
            userId: collab.userId,
            username: collab.username,
            message: `${collab.username} left the document`,
            documentId,
          })
        }
      })

      // Update the session
      state.setSession(documentId, { collaborators })
    }
  },

  addNotification: (notification) => {
    set((state) => {
      const newNotification: CollaborationNotification = {
        ...notification,
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        timestamp: new Date(),
      }

      const notifications = [newNotification, ...state.notifications].slice(
        0,
        state.maxNotifications
      )

      return { notifications }
    })
  },

  clearNotifications: () => {
    set({ notifications: [] })
  },

  dismissNotification: (id) => {
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    }))
  },

  getSession: (documentId) => {
    return get().activeSessions.get(documentId)
  },

  getCollaboratorsForDocument: (documentId) => {
    const session = get().activeSessions.get(documentId)
    return session?.collaborators ?? []
  },
}))

export default useCollaborationStore
