export type CollaborationConnectionPhase =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'error'

export interface CollaborationConnectionMachineState {
  phase: CollaborationConnectionPhase
  isOffline: boolean
  isSynced: boolean
  reconnectAttempt: number
  error: string | null
}

export type CollaborationConnectionMachineEvent =
  | { type: 'CONNECT_REQUESTED' }
  | { type: 'CONNECT_SUCCEEDED' }
  | { type: 'CONNECT_FAILED'; error: string }
  | { type: 'SYNCED' }
  | { type: 'DISCONNECTED' }
  | { type: 'RECONNECT_SCHEDULED'; attempt: number; delayMs: number; maxAttempts: number }
  | { type: 'RECONNECT_RESET' }
  | { type: 'ONLINE' }
  | { type: 'OFFLINE' }
  | { type: 'RESET'; isOffline: boolean }

export function createInitialCollaborationConnectionState(
  isOffline: boolean,
): CollaborationConnectionMachineState {
  return {
    phase: 'idle',
    isOffline,
    isSynced: false,
    reconnectAttempt: 0,
    error: null,
  }
}

export function transitionCollaborationConnectionState(
  state: CollaborationConnectionMachineState,
  event: CollaborationConnectionMachineEvent,
): CollaborationConnectionMachineState {
  switch (event.type) {
    case 'CONNECT_REQUESTED':
      if (state.isOffline) {
        return state
      }
      return {
        ...state,
        phase: 'connecting',
        isSynced: false,
        error: null,
      }
    case 'CONNECT_SUCCEEDED':
      return {
        ...state,
        phase: 'connected',
        isSynced: false,
        reconnectAttempt: 0,
        error: null,
      }
    case 'CONNECT_FAILED':
      return {
        ...state,
        phase: 'error',
        error: event.error,
      }
    case 'SYNCED':
      if (state.phase !== 'connected') {
        return state
      }
      return {
        ...state,
        isSynced: true,
      }
    case 'DISCONNECTED':
      return {
        ...state,
        phase: state.isOffline ? 'idle' : 'error',
        isSynced: false,
      }
    case 'RECONNECT_SCHEDULED':
      return {
        ...state,
        phase: 'reconnecting',
        isSynced: false,
        reconnectAttempt: event.attempt,
        error: `Connection lost. Reconnecting in ${Math.round(event.delayMs / 1000)}s... (attempt ${event.attempt}/${event.maxAttempts})`,
      }
    case 'RECONNECT_RESET':
      return {
        ...state,
        reconnectAttempt: 0,
        error: null,
      }
    case 'ONLINE':
      return {
        ...state,
        isOffline: false,
      }
    case 'OFFLINE':
      return {
        ...state,
        phase: 'idle',
        isOffline: true,
        isSynced: false,
      }
    case 'RESET':
      return createInitialCollaborationConnectionState(event.isOffline)
    default:
      return state
  }
}

export function toCollaborationConnectionFlags(state: CollaborationConnectionMachineState) {
  return {
    isConnected: state.phase === 'connected',
    isConnecting: state.phase === 'connecting' || state.phase === 'reconnecting',
    isSynced: state.isSynced,
    isOffline: state.isOffline,
    reconnectAttempt: state.reconnectAttempt,
    error: state.error,
  }
}

