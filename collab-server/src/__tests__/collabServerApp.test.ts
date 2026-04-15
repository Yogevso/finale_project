import {
  CollabServerApp,
  PERSISTENCE_FAILURE_MESSAGE,
  encodeCollabServerStatelessMessage,
  createRuntimeDependencies,
  resolveCollabServerConfigFromEnv,
} from '../server/collabServerApp.js';
import { verifyCollabToken as verifyCollabTokenFn } from '../auth.js';
import { saveDocument as saveDocumentFn } from '../persistence.js';
import { jest } from '@jest/globals';
import type { CollaborationPermission } from '../authContext/contracts.js';

describe('CollabServerApp config and runtime composition', () => {
  it('resolves defaults from environment when variables are missing', () => {
    const config = resolveCollabServerConfigFromEnv({});

    expect(config.port).toBe(8002);
    expect(config.host).toBe('0.0.0.0');
    expect(config.redisUrl).toBe('');
    expect(config.cacheInvalidationSecret).toBe('');
    expect(config.debounceMs).toBe(2000);
    expect(config.maxDebounceMs).toBe(10000);
    expect(config.healthPort).toBe(8003);
  });

  it('resolves explicit environment values', () => {
    const config = resolveCollabServerConfigFromEnv({
      PORT: '9000',
      HOST: '127.0.0.1',
      REDIS_URL: 'redis://localhost:6379',
      CACHE_INVALIDATION_SECRET: 'cache-secret',
      DEBOUNCE_MS: '1500',
      MAX_DEBOUNCE_MS: '7000',
    });

    expect(config.port).toBe(9000);
    expect(config.host).toBe('127.0.0.1');
    expect(config.redisUrl).toBe('redis://localhost:6379');
    expect(config.cacheInvalidationSecret).toBe('cache-secret');
    expect(config.debounceMs).toBe(1500);
    expect(config.maxDebounceMs).toBe(7000);
    expect(config.healthPort).toBe(9001);
    expect(config.maxTotalConnections).toBe(200);
    expect(config.maxConnectionsPerDocument).toBe(25);
    expect(config.reconnectWindowSeconds).toBe(60);
  });

  it('resolves explicit collaboration guardrails from the environment', () => {
    const config = resolveCollabServerConfigFromEnv({
      COLLAB_MAX_TOTAL_CONNECTIONS: '80',
      COLLAB_MAX_CONNECTIONS_PER_DOCUMENT: '6',
      COLLAB_RECONNECT_WINDOW_SECONDS: '45',
    });

    expect(config.maxTotalConnections).toBe(80);
    expect(config.maxConnectionsPerDocument).toBe(6);
    expect(config.reconnectWindowSeconds).toBe(45);
  });

  it('uses SECRET_KEY for cache invalidation fallback before JWT_SECRET', () => {
    const config = resolveCollabServerConfigFromEnv({
      SECRET_KEY: 'shared-secret',
      JWT_SECRET: 'legacy-secret',
    });

    expect(config.cacheInvalidationSecret).toBe('shared-secret');
  });

  it('allows runtime dependency overrides', () => {
    const customVerify = jest.fn();
    const runtime = createRuntimeDependencies({
      verifyCollabToken: customVerify as unknown as typeof verifyCollabTokenFn,
    });

    expect(runtime.verifyCollabToken).toBe(customVerify);
  });

  it('broadcasts a stateless warning when document persistence cannot run', async () => {
    const broadcastStateless = jest.fn();
    const saveDocument = jest.fn();
    const app = new CollabServerApp({
      runtimeOverrides: {
        extractDocumentId: jest.fn(() => '123'),
        getDocumentTokenForStore: jest.fn(() => null),
        saveDocument: saveDocument as unknown as typeof saveDocumentFn,
      },
    });

    await (app as any).handleStoreDocument({
      documentName: 'document/123',
      document: { broadcastStateless },
      state: Buffer.from([1, 2, 3]),
    });

    expect(saveDocument).not.toHaveBeenCalled();
    expect(broadcastStateless).toHaveBeenCalledWith(
      encodeCollabServerStatelessMessage({
        type: 'persistence_failed',
        message: PERSISTENCE_FAILURE_MESSAGE,
      }),
    );
  });

  it('clears the warning after a later successful save', async () => {
    const broadcastStateless = jest.fn();
    const saveDocument = jest
      .fn<(...args: unknown[]) => Promise<{ success: boolean; error?: string }>>()
      .mockResolvedValueOnce({ success: false, error: 'backend timeout' })
      .mockResolvedValueOnce({ success: true });
    const app = new CollabServerApp({
      runtimeOverrides: {
        extractDocumentId: jest.fn(() => '123'),
        getDocumentTokenForStore: jest.fn(() => 'write-token'),
        saveDocument: saveDocument as unknown as typeof saveDocumentFn,
      },
    });
    const payload = {
      documentName: 'document/123',
      document: { broadcastStateless },
      state: Buffer.from([1, 2, 3]),
    };

    await (app as any).handleStoreDocument(payload);
    await (app as any).handleStoreDocument(payload);

    expect(broadcastStateless.mock.calls).toEqual([
      [
        encodeCollabServerStatelessMessage({
          type: 'persistence_failed',
          message: PERSISTENCE_FAILURE_MESSAGE,
        }),
      ],
      [
        encodeCollabServerStatelessMessage({
          type: 'persistence_restored',
        }),
      ],
    ]);
  });

  it('rejects websocket authentication when backend tenant verification fails', async () => {
    const app = new CollabServerApp({
      runtimeOverrides: {
        extractDocumentId: jest.fn(() => '123'),
        verifyCollabToken: jest.fn(() => ({
          success: true,
          user: {
            userId: '1',
            username: 'editor',
            email: 'editor@example.com',
            role: 'editor',
            color: '#123456',
            traceId: 'trace-123',
          },
          permissions: ['read', 'write'] as CollaborationPermission[],
        })),
        verifyCollaborationAccess: jest.fn(async () => ({
          success: false,
          error: 'Cross-tenant collaboration is not allowed',
        })),
        registerDocumentConnectionAuth: jest.fn(),
        unregisterDocumentConnectionAuth: jest.fn(() => 0),
        clearDocumentAuth: jest.fn(),
        clearDocumentCache: jest.fn(),
      },
    });

    await expect(
      (app as any).authenticateConnection({
        documentName: 'document/123',
        token: 'collab-token',
        connection: {},
      }),
    ).rejects.toThrow('Cross-tenant collaboration is not allowed');
  });

  it('uses backend-verified permissions to mark downgraded sessions read-only', async () => {
    const registerDocumentConnectionAuth = jest.fn();
    const canWrite = jest.fn((permissions: string[]) => permissions.includes('write'));
    const app = new CollabServerApp({
      runtimeOverrides: {
        extractDocumentId: jest.fn(() => '123'),
        verifyCollabToken: jest.fn(() => ({
          success: true,
          user: {
            userId: '1',
            username: 'editor',
            email: 'editor@example.com',
            role: 'editor',
            color: '#123456',
            traceId: 'trace-123',
          },
          permissions: ['read', 'write'] as CollaborationPermission[],
        })),
        verifyCollaborationAccess: jest.fn(async () => ({
          success: true,
          permissions: ['read'] as CollaborationPermission[],
        })),
        canWrite: canWrite as any,
        registerDocumentConnectionAuth,
        unregisterDocumentConnectionAuth: jest.fn(() => 0),
        clearDocumentAuth: jest.fn(),
        clearDocumentCache: jest.fn(),
      },
    });
    const connection: { readOnly?: boolean } = {};

    const result = await (app as any).authenticateConnection({
      documentName: 'document/123',
      token: 'collab-token',
      connection,
    });

    expect(canWrite).toHaveBeenCalledWith(['read']);
    expect(connection.readOnly).toBe(true);
    expect(result.permissions).toEqual(['read']);
    expect((app as any).runtime.verifyCollaborationAccess).toHaveBeenCalledWith(
      '123',
      'collab-token',
      'trace-123',
    );
    expect(registerDocumentConnectionAuth).toHaveBeenCalledWith(
      expect.objectContaining({
        documentId: '123',
        token: 'collab-token',
        writeCapable: false,
      }),
    );
  });

  it('rejects connections when a document reaches the configured capacity and exposes guardrail telemetry', async () => {
    const registerDocumentConnectionAuth = jest.fn();
    const unregisterDocumentConnectionAuth = jest.fn(() => 0);
    const app = new CollabServerApp({
      config: {
        port: 8002,
        host: '127.0.0.1',
        redisUrl: '',
        cacheInvalidationSecret: '',
        debounceMs: 2000,
        maxDebounceMs: 10000,
        healthPort: 8003,
        maxTotalConnections: 10,
        maxConnectionsPerDocument: 1,
        reconnectWindowSeconds: 60,
      },
      runtimeOverrides: {
        extractDocumentId: jest.fn(() => '123'),
        verifyCollabToken: jest
          .fn<(token: string, documentId: string) => ReturnType<typeof verifyCollabTokenFn>>()
          .mockImplementation((token: string) => ({
            success: true,
            user: {
              userId: token === 'token-1' ? '1' : '2',
              username: token === 'token-1' ? 'editor-1' : 'editor-2',
              email: 'editor@example.com',
              role: 'editor',
              color: '#123456',
              traceId: `trace-${token}`,
            },
            permissions: ['read', 'write'] as CollaborationPermission[],
          })),
        verifyCollaborationAccess: jest.fn(async () => ({
          success: true,
          permissions: ['read', 'write'] as CollaborationPermission[],
        })),
        registerDocumentConnectionAuth,
        unregisterDocumentConnectionAuth,
        clearDocumentAuth: jest.fn(),
        clearDocumentCache: jest.fn(),
      },
    });

    await (app as any).authenticateConnection({
      documentName: 'document/123',
      token: 'token-1',
      connection: {},
    });

    await expect(
      (app as any).authenticateConnection({
        documentName: 'document/123',
        token: 'token-2',
        connection: {},
      }),
    ).rejects.toThrow('This document collaboration session is at capacity');

    const snapshot = (app as any).getServerInfo();
    expect(snapshot.status).toBe('degraded');
    expect(snapshot.saturation).toBe('saturated');
    expect(snapshot.totalConnections).toBe(1);
    expect(snapshot.guardrails.maxConnectionsPerDocument).toBe(1);
    expect(snapshot.guardrails.totalRejectedConnections).toBe(1);
    expect(snapshot.guardrails.rejectionsByReason.document_limit).toBe(1);
    expect(snapshot.documents.topDocuments).toEqual([
      {
        documentId: '123',
        totalConnections: 1,
        writeConnections: 1,
        readConnections: 0,
      },
    ]);
    expect(registerDocumentConnectionAuth).toHaveBeenCalledTimes(1);
  });
});
