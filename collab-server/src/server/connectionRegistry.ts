import type { ConnectionContext } from '../types.js';

type RegisterDocumentConnectionAuth = (params: {
  documentId: string;
  connectionId: string;
  token: string;
  writeCapable: boolean;
}) => void;

type UnregisterDocumentConnectionAuth = (documentId: string, connectionId: string) => number;
type ClearDocumentAuth = (documentId: string) => void;
type ClearDocumentCache = (documentId: string) => void;

export interface ConnectionRegistryHooks {
  registerDocumentConnectionAuth: RegisterDocumentConnectionAuth;
  unregisterDocumentConnectionAuth: UnregisterDocumentConnectionAuth;
  clearDocumentAuth: ClearDocumentAuth;
  clearDocumentCache: ClearDocumentCache;
}

export interface DocumentConnectionSnapshot {
  documentId: string;
  totalConnections: number;
  writeConnections: number;
  readConnections: number;
}

export interface ConnectionRegistrySnapshot {
  activeDocuments: number;
  totalConnections: number;
  maxConnectionsOnSingleDocument: number;
  documents: DocumentConnectionSnapshot[];
}

export class ConnectionRegistry {
  private readonly activeConnections = new Map<string, Map<string, ConnectionContext>>();
  private readonly connectionsByUser = new Map<string, Map<string, Set<string>>>();

  constructor(private readonly hooks: ConnectionRegistryHooks) {}

  register(params: { connection: ConnectionContext; token: string; writeCapable: boolean }): void {
    const { connection, token, writeCapable } = params;
    const documentId = connection.documentId;

    if (!this.activeConnections.has(documentId)) {
      this.activeConnections.set(documentId, new Map());
    }
    if (!this.connectionsByUser.has(documentId)) {
      this.connectionsByUser.set(documentId, new Map());
    }
    this.activeConnections.get(documentId)!.set(connection.connectionId, connection);
    const documentUserConnections = this.connectionsByUser.get(documentId)!;
    const userConnections = documentUserConnections.get(connection.userId) ?? new Set<string>();
    userConnections.add(connection.connectionId);
    documentUserConnections.set(connection.userId, userConnections);
    this.hooks.registerDocumentConnectionAuth({
      documentId,
      connectionId: connection.connectionId,
      token,
      writeCapable,
    });
  }

  unregister(params: { documentId: string; connectionId?: string; userId?: string }): boolean {
    const { documentId, connectionId, userId } = params;
    const docConnections = this.activeConnections.get(documentId);
    if (!docConnections) {
      return false;
    }

    let removedConnectionId: string | undefined;

    if (connectionId && docConnections.has(connectionId)) {
      const removedConnection = docConnections.get(connectionId)!;
      docConnections.delete(connectionId);
      this.removeUserConnection(documentId, removedConnection.userId, connectionId);
      removedConnectionId = connectionId;
    } else if (userId) {
      const userConnections = this.connectionsByUser.get(documentId)?.get(userId);
      const trackedConnectionId = userConnections?.values().next().value;
      if (trackedConnectionId && docConnections.has(trackedConnectionId)) {
        docConnections.delete(trackedConnectionId);
        this.removeUserConnection(documentId, userId, trackedConnectionId);
        removedConnectionId = trackedConnectionId;
      }
    }

    if (!removedConnectionId) {
      return false;
    }

    this.hooks.unregisterDocumentConnectionAuth(documentId, removedConnectionId);
    if (docConnections.size === 0) {
      this.activeConnections.delete(documentId);
      this.connectionsByUser.delete(documentId);
      this.hooks.clearDocumentAuth(documentId);
      this.hooks.clearDocumentCache(documentId);
    }
    return true;
  }

  private removeUserConnection(documentId: string, userId: string, connectionId: string): void {
    const documentUserConnections = this.connectionsByUser.get(documentId);
    if (!documentUserConnections) {
      return;
    }

    const userConnections = documentUserConnections.get(userId);
    if (!userConnections) {
      return;
    }

    userConnections.delete(connectionId);
    if (userConnections.size === 0) {
      documentUserConnections.delete(userId);
    }
    if (documentUserConnections.size === 0) {
      this.connectionsByUser.delete(documentId);
    }
  }

  getTotalConnections(): number {
    let totalConnections = 0;
    for (const connections of this.activeConnections.values()) {
      totalConnections += connections.size;
    }
    return totalConnections;
  }

  getDocumentConnectionCount(documentId: string): number {
    return this.activeConnections.get(documentId)?.size ?? 0;
  }

  getSnapshot(limit = 5): ConnectionRegistrySnapshot {
    const documents: DocumentConnectionSnapshot[] = [];
    let maxConnectionsOnSingleDocument = 0;

    for (const [documentId, connections] of this.activeConnections.entries()) {
      let writeConnections = 0;
      let readConnections = 0;
      for (const connection of connections.values()) {
        if (connection.canWrite) {
          writeConnections += 1;
        } else {
          readConnections += 1;
        }
      }

      const totalConnections = connections.size;
      maxConnectionsOnSingleDocument = Math.max(maxConnectionsOnSingleDocument, totalConnections);
      documents.push({
        documentId,
        totalConnections,
        writeConnections,
        readConnections,
      });
    }

    documents.sort((left, right) => {
      if (right.totalConnections !== left.totalConnections) {
        return right.totalConnections - left.totalConnections;
      }
      return left.documentId.localeCompare(right.documentId);
    });

    return {
      activeDocuments: this.activeConnections.size,
      totalConnections: this.getTotalConnections(),
      maxConnectionsOnSingleDocument,
      documents: documents.slice(0, Math.max(1, limit)),
    };
  }
}
