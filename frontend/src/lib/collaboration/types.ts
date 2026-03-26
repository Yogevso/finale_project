import { HocuspocusProvider } from '@hocuspocus/provider'
import * as Y from 'yjs'

export interface CollaboratorInfo {
  clientId: number
  userId: string
  username: string
  color: string
  cursor?: {
    anchor: number
    head: number
  }
}

export interface CollaborationState {
  isConnected: boolean
  isConnecting: boolean
  isSynced: boolean
  isOffline: boolean
  isReadOnly: boolean
  hasLocalChanges: boolean
  reconnectAttempt: number
  permissions: string[]
  error: string | null
  persistenceWarning: string | null
  collaborators: CollaboratorInfo[]
  provider: HocuspocusProvider | null
  ydoc: Y.Doc | null
}

export interface UseCollaborationOptions {
  documentId: number
  documentTitle?: string
  username: string
  userId: string | number
  enabled?: boolean
  autoReconnect?: boolean
  maxReconnectAttempts?: number
  autoSaveInterval?: number
  onConnect?: () => void
  onDisconnect?: () => void
  onSynced?: () => void
  onError?: (error: Error) => void
  onOfflineChange?: (isOffline: boolean) => void
  onPermissionChange?: (permissions: string[], isReadOnly: boolean) => void
}

export interface UseCollaborationReturn extends CollaborationState {
  connect: () => Promise<void>
  disconnect: () => void
  reconnect: () => Promise<void>
  getFragment: (name?: string) => Y.XmlFragment | null
  clearLocalData: () => Promise<void>
  refreshPermissions: () => Promise<void>
  canEdit: () => boolean
  createSnapshot: (name?: string) => Promise<void>
  sessionId: string | null
}

export interface CollaborationAuthResponse {
  token: string
  permissions?: string[]
  websocket_url?: string
}
