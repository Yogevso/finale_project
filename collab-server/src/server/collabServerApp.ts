import { randomUUID } from 'crypto';

import { Database } from '@hocuspocus/extension-database';
import { Logger } from '@hocuspocus/extension-logger';
import { Redis } from '@hocuspocus/extension-redis';
import { Extension, Server } from '@hocuspocus/server';
import * as Y from 'yjs';

import { canWrite, extractDocumentId, extractToken, verifyCollabToken } from '../auth.js';
import {
  clearDocumentAuth,
  getDocumentTokenForLoad,
  getDocumentTokenForStore,
  registerDocumentConnectionAuth,
  unregisterDocumentConnectionAuth,
} from '../documentAuthStore.js';
import { clearDocumentCache, loadDocument, saveDocument } from '../persistence.js';
import type { AwarenessUser, ConnectionContext } from '../types.js';
import { getUserColor } from '../types.js';
import { ConnectionRegistry } from './connectionRegistry.js';
import { HealthServer } from './healthServer.js';

type HocuspocusServer = ReturnType<typeof Server.configure>;

export interface CollabServerConfig {
  port: number;
  host: string;
  redisUrl: string;
  debounceMs: number;
  maxDebounceMs: number;
  healthPort: number;
}

export type CollabRuntimeDependencies = {
  verifyCollabToken: typeof verifyCollabToken;
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

export function resolveCollabServerConfigFromEnv(
  env: NodeJS.ProcessEnv = process.env,
): CollabServerConfig {
  const port = parseInt(env.PORT || '8002', 10);
  return {
    port,
    host: env.HOST || '0.0.0.0',
    redisUrl: env.REDIS_URL || '',
    debounceMs: parseInt(env.DEBOUNCE_MS || '2000', 10),
    maxDebounceMs: parseInt(env.MAX_DEBOUNCE_MS || '10000', 10),
    healthPort: port + 1,
  };
}

export function createRuntimeDependencies(
  overrides: Partial<CollabRuntimeDependencies> = {},
): CollabRuntimeDependencies {
  return {
    verifyCollabToken,
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
    this.server = this.configureServer();
  }

  async start(): Promise<void> {
    if (this.started) {
      return;
    }

    await this.healthServer.start();
    console.log(
      `[Health] HTTP health check available at http://${this.config.host}:${this.healthServer.port}/health`,
    );

    await this.server.listen();
    console.log(`[Server] Hocuspocus server running on ws://${this.config.host}:${this.config.port}`);
    console.log(
      `[Server] Connect to: ws://${this.config.host}:${this.config.port}/document/{documentId}?token={jwt}`,
    );
    this.started = true;
  }

  async stop(): Promise<void> {
    if (!this.started) {
      return;
    }

    await this.server.destroy();
    await this.healthServer.stop();
    this.started = false;
  }

  printStartupBanner(): void {
    console.log('============================================');
    console.log('  Hocuspocus Collaboration Server');
    console.log('============================================');
    console.log(`  WebSocket Port: ${this.config.port}`);
    console.log(`  Health Port: ${this.config.healthPort}`);
    console.log(`  Host: ${this.config.host}`);
    console.log(
      `  Redis: ${this.config.redisUrl ? `ENABLED (${this.config.redisUrl})` : 'DISABLED (single-server mode)'}`,
    );
    console.log('============================================');
  }

  private buildExtensions(): Extension[] {
    const extensions: Extension[] = [
      new Logger({
        log: (message) => {
          console.log(`[Hocuspocus] ${message}`);
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

            if (!token) {
              console.log(`[Database] No token available for document ${documentId}`);
              return null;
            }

            return this.runtime.loadDocument(documentId, token);
          },
          store: async ({ documentName, state }) => {
            const documentId = this.runtime.extractDocumentId(documentName);
            const token = this.runtime.getDocumentTokenForStore(documentId);

            if (!token) {
              console.error(
                `[Database] No write-capable token available to save document ${documentId}`,
              );
              return;
            }

            await this.runtime.saveDocument(documentId, state, token);
          },
        }),
      ],
      onAuthenticate: async ({ documentName, token: rawToken, requestParameters, connection }) => {
        const documentId = this.runtime.extractDocumentId(documentName);
        const token = rawToken || this.runtime.extractToken(requestParameters);
        if (!token) {
          throw new Error('No authentication token provided');
        }

        const authResult = this.runtime.verifyCollabToken(token, documentId);
        if (!authResult.success || !authResult.user) {
          throw new Error(authResult.error || 'Authentication failed');
        }

        const writeCapable = this.runtime.canWrite(authResult.permissions || []);
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
        console.log(
          `[Auth] User ${authResult.user.username} authenticated for document ${documentId} (readonly: ${connection.readOnly})`,
        );

        return {
          user: authResult.user,
          permissions: authResult.permissions,
          connectionId: connectionContext.connectionId,
        };
      },
      onLoadDocument: async ({ documentName }) => {
        const documentId = this.runtime.extractDocumentId(documentName);
        console.log(`[Document] Loading document ${documentId}`);
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

        if (user) {
          console.log(`[Disconnect] User ${user.username} left document ${documentId}`);
        }
      },
      onStoreDocument: async ({ documentName, document }) => {
        const documentId = this.runtime.extractDocumentId(documentName);
        const state = Y.encodeStateAsUpdate(document);
        console.log(`[Store] Final save for document ${documentId} (${state.length} bytes)`);
      },
    });
  }

  private getServerInfo() {
    return this.connectionRegistry.getServerInfo(this.config.port, process.uptime());
  }
}
