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
      .fn()
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
          permissions: ['read', 'write'],
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
          permissions: ['read', 'write'],
        })),
        verifyCollaborationAccess: jest.fn(async () => ({
          success: true,
          permissions: ['read'],
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
});
