/**
 * Tracks per-document auth tokens by connection, preserving write-capable tokens.
 */

import jwt from 'jsonwebtoken';

import { isCollaborationTokenContract } from './authContext/contracts.js';

interface DocumentAuthState {
  tokensByConnection: Map<string, string>;
  writeConnectionIds: Set<string>;
  lastAccess: number;
}

const documentAuth = new Map<string, DocumentAuthState>();

/** Maximum age (ms) before a document auth entry is considered stale. */
const AUTH_TTL_MS = 60 * 60 * 1000; // 1 hour

/** How often the sweep runs (ms). */
const SWEEP_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

function sweepStaleEntries(): void {
  const now = Date.now();
  for (const [docId, state] of documentAuth) {
    if (now - state.lastAccess > AUTH_TTL_MS) {
      documentAuth.delete(docId);
    }
  }
}

const sweepTimer = setInterval(sweepStaleEntries, SWEEP_INTERVAL_MS);
sweepTimer.unref(); // don't keep the process alive for cleanup

function getOrCreateState(documentId: string): DocumentAuthState {
  const existing = documentAuth.get(documentId);
  if (existing) {
    existing.lastAccess = Date.now();
    return existing;
  }
  const state: DocumentAuthState = {
    tokensByConnection: new Map<string, string>(),
    writeConnectionIds: new Set<string>(),
    lastAccess: Date.now(),
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

function tokenMatchesDocument(token: string, documentId: string): boolean {
  const decoded = jwt.decode(token);
  return isCollaborationTokenContract(decoded) && decoded.document_id === documentId;
}

export function registerDocumentConnectionAuth(params: {
  documentId: string;
  connectionId: string;
  token: string;
  writeCapable: boolean;
}): void {
  const { documentId, connectionId, token, writeCapable } = params;
  if (!tokenMatchesDocument(token, documentId)) {
    throw new Error('Token is not valid for this document');
  }
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
  state.lastAccess = Date.now();
  return getWriteToken(state) ?? getFirstToken(state);
}

export function getDocumentTokenForStore(documentId: string): string | null {
  const state = documentAuth.get(documentId);
  if (!state) {
    return null;
  }
  state.lastAccess = Date.now();
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
