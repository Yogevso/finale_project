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

export interface CollabServerInfo {
  name: 'collab-server';
  status: 'healthy';
  port: number;
  activeDocuments: number;
  totalConnections: number;
  uptime: number;
}

export class ConnectionRegistry {
  private readonly activeConnections = new Map<string, Map<string, ConnectionContext>>();

  constructor(private readonly hooks: ConnectionRegistryHooks) {}

  register(params: { connection: ConnectionContext; token: string; writeCapable: boolean }): void {
    const { connection, token, writeCapable } = params;
    const documentId = connection.documentId;

    if (!this.activeConnections.has(documentId)) {
      this.activeConnections.set(documentId, new Map());
    }
    this.activeConnections.get(documentId)!.set(connection.connectionId, connection);
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
      docConnections.delete(connectionId);
      removedConnectionId = connectionId;
    } else if (userId) {
      for (const [trackedConnectionId, tracked] of docConnections.entries()) {
        if (tracked.userId === userId) {
          docConnections.delete(trackedConnectionId);
          removedConnectionId = trackedConnectionId;
          break;
        }
      }
    }

    if (!removedConnectionId) {
      return false;
    }

    this.hooks.unregisterDocumentConnectionAuth(documentId, removedConnectionId);
    if (docConnections.size === 0) {
      this.activeConnections.delete(documentId);
      this.hooks.clearDocumentAuth(documentId);
      this.hooks.clearDocumentCache(documentId);
    }
    return true;
  }

  getServerInfo(port: number, uptime: number): CollabServerInfo {
    let totalConnections = 0;
    for (const connections of this.activeConnections.values()) {
      totalConnections += connections.size;
    }

    return {
      name: 'collab-server',
      status: 'healthy',
      port,
      activeDocuments: this.activeConnections.size,
      totalConnections,
      uptime,
    };
  }
}
