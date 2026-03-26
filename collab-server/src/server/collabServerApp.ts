import { randomUUID } from 'crypto';
import { performance } from 'node:perf_hooks';

import { Database } from '@hocuspocus/extension-database';
import { Logger } from '@hocuspocus/extension-logger';
import { Redis } from '@hocuspocus/extension-redis';
import { Extension, Server, type storePayload } from '@hocuspocus/server';
import * as Y from 'yjs';

import { verifyCollaborationAccess } from '../adapters/backendCollaborationAuthAdapter.js';
import { canWrite, extractDocumentId, extractToken, verifyCollabToken } from '../auth.js';
import {
  clearDocumentAuth,
  getDocumentTokenForLoad,
  getDocumentTokenForStore,
  registerDocumentConnectionAuth,
  unregisterDocumentConnectionAuth,
} from '../documentAuthStore.js';
import { createStructuredLogger } from '../logger.js';
import { clearDocumentCache, initCacheInvalidation, loadDocument, saveDocument, stopCacheInvalidation } from '../persistence.js';
import type { AwarenessUser, ConnectionContext } from '../types.js';
import { getUserColor } from '../types.js';
import { ConnectionRegistry } from './connectionRegistry.js';
import { CollabRuntimeMetrics } from './collabRuntimeMetrics.js';
import { HealthServer } from './healthServer.js';

type HocuspocusServer = ReturnType<typeof Server.configure>;

export interface CollabServerConfig {
  port: number;
  host: string;
  redisUrl: string;
  cacheInvalidationSecret: string;
  debounceMs: number;
  maxDebounceMs: number;
  healthPort: number;
  maxTotalConnections: number;
  maxConnectionsPerDocument: number;
  reconnectWindowSeconds: number;
}

export type CollabRuntimeDependencies = {
  verifyCollabToken: typeof verifyCollabToken;
  verifyCollaborationAccess: typeof verifyCollaborationAccess;
  extractToken: typeof extractToken;
  extractDocumentId: typeof extractDocumentId;
  canWrite: typeof canWrite;
  loadDocument: typeof loadDocument;
  saveDocument: typeof saveDocument;
  clearDocumentCache: typeof clearDocumentCache;
  clearDocumentAuth: typeof clearDocumentAuth;
  getDocumentTokenForLoad: typeof getDocumentTokenForLoad;
  getDocumentTokenForStore: typeof getDocumentTokenForStore;
  registerDocumentConnectionAuth: typeof registerDocumentConnectionAuth;
  unregisterDocumentConnectionAuth: typeof unregisterDocumentConnectionAuth;
};

const logger = createStructuredLogger('collab.server');

export const PERSISTENCE_FAILURE_MESSAGE =
  'Changes are no longer being saved to the server. Keep this tab open and reconnect before closing it.';

export type CollabServerStatelessMessage =
  | {
      type: 'persistence_failed';
      message: string;
    }
  | {
      type: 'persistence_restored';
    };

export function encodeCollabServerStatelessMessage(
  message: CollabServerStatelessMessage,
): string {
  return JSON.stringify(message);
}

export function resolveCollabServerConfigFromEnv(
  env: NodeJS.ProcessEnv = process.env,
): CollabServerConfig {
  const port = parseInt(env.PORT || '8002', 10);
  return {
    port,
    host: env.HOST || '0.0.0.0',
    redisUrl: env.REDIS_URL || '',
    cacheInvalidationSecret: env.CACHE_INVALIDATION_SECRET || env.SECRET_KEY || env.JWT_SECRET || '',
    debounceMs: parseInt(env.DEBOUNCE_MS || '2000', 10),
    maxDebounceMs: parseInt(env.MAX_DEBOUNCE_MS || '10000', 10),
    healthPort: port + 1,
    maxTotalConnections: parseInt(env.COLLAB_MAX_TOTAL_CONNECTIONS || '200', 10),
    maxConnectionsPerDocument: parseInt(env.COLLAB_MAX_CONNECTIONS_PER_DOCUMENT || '25', 10),
    reconnectWindowSeconds: parseInt(env.COLLAB_RECONNECT_WINDOW_SECONDS || '60', 10),
  };
}

export function createRuntimeDependencies(
  overrides: Partial<CollabRuntimeDependencies> = {},
): CollabRuntimeDependencies {
  return {
    verifyCollabToken,
    verifyCollaborationAccess,
    extractToken,
    extractDocumentId,
    canWrite,
    loadDocument,
    saveDocument,
    clearDocumentCache,
    clearDocumentAuth,
    getDocumentTokenForLoad,
    getDocumentTokenForStore,
    registerDocumentConnectionAuth,
    unregisterDocumentConnectionAuth,
    ...overrides,
  };
}

export class CollabServerApp {
  private readonly config: CollabServerConfig;
  private readonly runtime: CollabRuntimeDependencies;
  private readonly connectionRegistry: ConnectionRegistry;
  private readonly healthServer: HealthServer;
  private readonly server: HocuspocusServer;
  private readonly runtimeMetrics: CollabRuntimeMetrics;
  private readonly documentsWithPersistenceFailures = new Set<string>();
  private started = false;

  constructor(params?: {
    config?: CollabServerConfig;
    runtimeOverrides?: Partial<CollabRuntimeDependencies>;
  }) {
    this.config = params?.config ?? resolveCollabServerConfigFromEnv();
    this.runtime = createRuntimeDependencies(params?.runtimeOverrides ?? {});
    this.connectionRegistry = new ConnectionRegistry({
      registerDocumentConnectionAuth: this.runtime.registerDocumentConnectionAuth,
      unregisterDocumentConnectionAuth: this.runtime.unregisterDocumentConnectionAuth,
      clearDocumentAuth: this.runtime.clearDocumentAuth,
      clearDocumentCache: this.runtime.clearDocumentCache,
    });
    this.healthServer = new HealthServer({
      host: this.config.host,
      port: this.config.healthPort,
      infoProvider: () => this.getServerInfo(),
    });
    this.runtimeMetrics = new CollabRuntimeMetrics({
      maxTotalConnections: this.config.maxTotalConnections,
      maxConnectionsPerDocument: this.config.maxConnectionsPerDocument,
      reconnectWindowSeconds: this.config.reconnectWindowSeconds,
    });
    this.server = this.configureServer();
  }

  async start(): Promise<void> {
    if (this.started) {
      return;
    }

    if (this.config.redisUrl) {
      await initCacheInvalidation(
        this.config.redisUrl,
        this.config.cacheInvalidationSecret,
      );
    }

    await this.healthServer.start();
    logger.info('Health endpoint available', {
      host: this.config.host,
      port: this.healthServer.port,
      path: '/health',
    });

    await this.server.listen();
    logger.info('Hocuspocus server running', {
      host: this.config.host,
      port: this.config.port,
      websocketUrl: `ws://${this.config.host}:${this.config.port}`,
    });
    logger.info('Collaboration connection template ready', {
      websocketUrlTemplate: `ws://${this.config.host}:${this.config.port}/document/{documentId}?token={jwt}`,
    });
    this.started = true;
  }

  async stop(): Promise<void> {
    if (!this.started) {
      return;
    }

    await this.server.destroy();
    await stopCacheInvalidation();
    await this.healthServer.stop();
    this.started = false;
  }

  printStartupBanner(): void {
    logger.info('Collaboration server configuration', {
      host: this.config.host,
      websocketPort: this.config.port,
      healthPort: this.config.healthPort,
      redisEnabled: Boolean(this.config.redisUrl),
      redisUrl: this.config.redisUrl || null,
      maxTotalConnections: this.config.maxTotalConnections,
      maxConnectionsPerDocument: this.config.maxConnectionsPerDocument,
      reconnectWindowSeconds: this.config.reconnectWindowSeconds,
    });
  }

  private broadcastPersistenceFailure(documentId: string, payload: storePayload): void {
    if (this.documentsWithPersistenceFailures.has(documentId)) {
      return;
    }

    this.documentsWithPersistenceFailures.add(documentId);
    this.runtimeMetrics.recordPersistenceFailure(documentId);
    payload.document.broadcastStateless(
      encodeCollabServerStatelessMessage({
        type: 'persistence_failed',
        message: PERSISTENCE_FAILURE_MESSAGE,
      }),
    );
  }

  private clearPersistenceFailure(documentId: string, payload: storePayload): void {
    if (!this.documentsWithPersistenceFailures.delete(documentId)) {
      return;
    }

    this.runtimeMetrics.recordPersistenceRestored(documentId);
    payload.document.broadcastStateless(
      encodeCollabServerStatelessMessage({
        type: 'persistence_restored',
      }),
    );
  }

  private readonly handleStoreDocument = async (payload: storePayload): Promise<void> => {
    const documentId = this.runtime.extractDocumentId(payload.documentName);
    const token = this.runtime.getDocumentTokenForStore(documentId);
    const startedAt = performance.now();

    if (!token) {
      logger.error('No write-capable token available to save document', { documentId });
      this.runtimeMetrics.recordDocumentSave({
        durationMs: performance.now() - startedAt,
        success: false,
        error: 'No write-capable token available to save document',
      });
      this.broadcastPersistenceFailure(documentId, payload);
      return;
    }

    const saveResult = await this.runtime.saveDocument(documentId, payload.state, token);
    if (!saveResult.success) {
      this.runtimeMetrics.recordDocumentSave({
        durationMs: performance.now() - startedAt,
        success: false,
        error: saveResult.error ?? 'Document save failed',
      });
      this.broadcastPersistenceFailure(documentId, payload);
      return;
    }

    this.runtimeMetrics.recordDocumentSave({
      durationMs: performance.now() - startedAt,
      success: true,
    });
    this.clearPersistenceFailure(documentId, payload);
  };

  private readonly authenticateConnection = async ({
    documentName,
    token: rawToken,
    connection,
  }: {
    documentName: string;
    token?: string;
    connection: { readOnly?: boolean };
  }) => {
    const documentId = this.runtime.extractDocumentId(documentName);
    // H-21: Only accept token from the WebSocket protocol message (first message),
    // not from URL query string, to avoid token leakage in server logs.
    const token = rawToken;
    if (!token) {
      this.runtimeMetrics.recordAuthenticationFailure();
      throw new Error('No authentication token provided');
    }

    const authResult = this.runtime.verifyCollabToken(token, documentId);
    if (!authResult.success || !authResult.user) {
      this.runtimeMetrics.recordAuthenticationFailure();
      throw new Error(authResult.error || 'Authentication failed');
    }

    const backendAuthResult = await this.runtime.verifyCollaborationAccess(
      documentId,
      token,
      authResult.user.traceId,
    );
    if (!backendAuthResult.success) {
      this.runtimeMetrics.recordAuthenticationFailure();
      throw new Error(backendAuthResult.error || 'Authentication failed');
    }

    const effectivePermissions = backendAuthResult.permissions || authResult.permissions || [];
    const writeCapable = this.runtime.canWrite(effectivePermissions);
    const currentTotalConnections = this.connectionRegistry.getTotalConnections();
    if (currentTotalConnections >= this.config.maxTotalConnections) {
      this.runtimeMetrics.recordConnectionRejected('total_limit');
      logger.warn('Rejected collaboration connection because the server is at capacity', {
        documentId,
        userId: authResult.user.userId,
        maxTotalConnections: this.config.maxTotalConnections,
        currentTotalConnections,
      });
      throw new Error('Collaboration server is at capacity');
    }

    const currentDocumentConnections = this.connectionRegistry.getDocumentConnectionCount(documentId);
    if (currentDocumentConnections >= this.config.maxConnectionsPerDocument) {
      this.runtimeMetrics.recordConnectionRejected('document_limit');
      logger.warn('Rejected collaboration connection because the document is at capacity', {
        documentId,
        userId: authResult.user.userId,
        maxConnectionsPerDocument: this.config.maxConnectionsPerDocument,
        currentDocumentConnections,
      });
      throw new Error('This document collaboration session is at capacity');
    }

    const connectionContext: ConnectionContext = {
      ...authResult.user,
      documentId,
      connectionId: randomUUID(),
      canWrite: writeCapable,
      connectedAt: new Date(),
    };

    if (!writeCapable) {
      connection.readOnly = true;
    }

    this.connectionRegistry.register({
      connection: connectionContext,
      token,
      writeCapable,
    });
    this.runtimeMetrics.recordConnectionAccepted({
      documentId,
      userId: authResult.user.userId,
    });
    logger.info('User authenticated for collaboration document', {
      traceId: authResult.user.traceId,
      username: authResult.user.username,
      documentId,
      readOnly: Boolean(connection.readOnly),
    });

    return {
      user: authResult.user,
      permissions: effectivePermissions,
      connectionId: connectionContext.connectionId,
    };
  };

  private buildExtensions(): Extension[] {
    const extensions: Extension[] = [
      new Logger({
        log: (message) => {
          logger.info('Hocuspocus runtime event', { message });
        },
        onLoadDocument: true,
        onStoreDocument: true,
        onConnect: true,
        onDisconnect: true,
        onChange: false,
      }),
    ];

    if (this.config.redisUrl) {
      const redisUrl = new URL(this.config.redisUrl);
      extensions.push(
        new Redis({
          host: redisUrl.hostname,
          port: parseInt(redisUrl.port || '6379', 10),
        }),
      );
    }

    return extensions;
  }

  private configureServer(): HocuspocusServer {
    return Server.configure({
      name: 'collab-server',
      port: this.config.port,
      address: this.config.host,
      debounce: this.config.debounceMs,
      maxDebounce: this.config.maxDebounceMs,
      quiet: true,
      extensions: [
        ...this.buildExtensions(),
        new Database({
          fetch: async ({ documentName }) => {
            const documentId = this.runtime.extractDocumentId(documentName);
            const token = this.runtime.getDocumentTokenForLoad(documentId);
            const startedAt = performance.now();

            if (!token) {
              logger.warn('No token available to load document', { documentId });
              this.runtimeMetrics.recordDocumentLoad({
                durationMs: performance.now() - startedAt,
                success: false,
                error: 'No token available to load document',
              });
              return null;
            }

            try {
              const state = await this.runtime.loadDocument(documentId, token);
              this.runtimeMetrics.recordDocumentLoad({
                durationMs: performance.now() - startedAt,
                success: true,
              });
              return state;
            } catch (error) {
              this.runtimeMetrics.recordDocumentLoad({
                durationMs: performance.now() - startedAt,
                success: false,
                error,
              });
              throw error;
            }
          },
          store: this.handleStoreDocument,
        }),
      ],
      onAuthenticate: this.authenticateConnection,
      onLoadDocument: async ({ documentName }) => {
        const documentId = this.runtime.extractDocumentId(documentName);
        logger.info('Loading collaboration document', { documentId });
      },
      onChange: async ({ documentName, document }) => {
        this.runtime.extractDocumentId(documentName);
        void document;
      },
      onAwarenessUpdate: async ({ states }) => {
        const users: AwarenessUser[] = [];
        states.forEach((state) => {
          if (state.user) {
            users.push({
              userId: state.user.userId,
              username: state.user.username,
              color: state.user.color || getUserColor(state.user.userId),
              cursor: state.cursor,
            });
          }
        });
      },
      onDisconnect: async ({ documentName, context }) => {
        const documentId = this.runtime.extractDocumentId(documentName);
        const user = context?.user;
        const connectionId = context?.connectionId as string | undefined;

        this.connectionRegistry.unregister({
          documentId,
          connectionId,
          userId: user?.userId,
        });
        this.runtimeMetrics.recordConnectionDisconnected({
          documentId,
          userId: user?.userId,
        });

        if (user) {
          logger.info('User disconnected from collaboration document', {
            traceId: user.traceId,
            username: user.username,
            documentId,
          });
        }
      },
      onStoreDocument: async ({ documentName, document }) => {
        const documentId = this.runtime.extractDocumentId(documentName);
        const state = Y.encodeStateAsUpdate(document);
        logger.info('Final collaboration document save', {
          documentId,
          bytes: state.length,
        });
      },
      afterUnloadDocument: async ({ documentName }) => {
        const documentId = this.runtime.extractDocumentId(documentName);
        this.documentsWithPersistenceFailures.delete(documentId);
      },
    });
  }

  private getServerInfo() {
    return this.runtimeMetrics.snapshot({
      port: this.config.port,
      uptime: process.uptime(),
      registry: this.connectionRegistry.getSnapshot(),
    });
  }
}
