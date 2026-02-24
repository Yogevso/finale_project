/**
 * Tracks per-document auth tokens by connection, preserving write-capable tokens.
 */

interface DocumentAuthState {
  tokensByConnection: Map<string, string>;
  writeConnectionIds: Set<string>;
}

const documentAuth = new Map<string, DocumentAuthState>();

function getOrCreateState(documentId: string): DocumentAuthState {
  const existing = documentAuth.get(documentId);
  if (existing) {
    return existing;
  }
  const state: DocumentAuthState = {
    tokensByConnection: new Map<string, string>(),
    writeConnectionIds: new Set<string>(),
  };
  documentAuth.set(documentId, state);
  return state;
}

function getFirstToken(state: DocumentAuthState): string | null {
  const first = state.tokensByConnection.values().next();
  if (first.done) {
    return null;
  }
  return first.value;
}

function getWriteToken(state: DocumentAuthState): string | null {
  for (const connectionId of state.writeConnectionIds.values()) {
    const token = state.tokensByConnection.get(connectionId);
    if (token) {
      return token;
    }
  }
  return null;
}

export function registerDocumentConnectionAuth(params: {
  documentId: string;
  connectionId: string;
  token: string;
  writeCapable: boolean;
}): void {
  const { documentId, connectionId, token, writeCapable } = params;
  const state = getOrCreateState(documentId);

  state.tokensByConnection.set(connectionId, token);
  if (writeCapable) {
    state.writeConnectionIds.add(connectionId);
  } else {
    state.writeConnectionIds.delete(connectionId);
  }
}

export function unregisterDocumentConnectionAuth(documentId: string, connectionId: string): number {
  const state = documentAuth.get(documentId);
  if (!state) {
    return 0;
  }

  state.tokensByConnection.delete(connectionId);
  state.writeConnectionIds.delete(connectionId);

  const remaining = state.tokensByConnection.size;
  if (remaining === 0) {
    documentAuth.delete(documentId);
  }
  return remaining;
}

export function getDocumentTokenForLoad(documentId: string): string | null {
  const state = documentAuth.get(documentId);
  if (!state) {
    return null;
  }
  return getWriteToken(state) ?? getFirstToken(state);
}

export function getDocumentTokenForStore(documentId: string): string | null {
  const state = documentAuth.get(documentId);
  if (!state) {
    return null;
  }
  return getWriteToken(state);
}

export function clearDocumentAuth(documentId: string): void {
  documentAuth.delete(documentId);
}

export function getDocumentAuthStats(documentId: string): {
  connections: number;
  writeConnections: number;
} {
  const state = documentAuth.get(documentId);
  return {
    connections: state?.tokensByConnection.size ?? 0,
    writeConnections: state?.writeConnectionIds.size ?? 0,
  };
}

export function getTrackedDocumentCount(): number {
  return documentAuth.size;
}
