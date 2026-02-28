import { ConnectionRegistry } from '../server/connectionRegistry.js';
import type { ConnectionRegistryHooks } from '../server/connectionRegistry.js';
import type { ConnectionContext } from '../types.js';
import { jest } from '@jest/globals';

function buildConnection(overrides: Partial<ConnectionContext> = {}): ConnectionContext {
  return {
    userId: 'user-1',
    username: 'User One',
    email: 'user1@example.com',
    role: 'editor',
    color: '#123456',
    documentId: 'doc-1',
    connectionId: 'conn-1',
    canWrite: true,
    connectedAt: new Date(),
    ...overrides,
  };
}

describe('ConnectionRegistry', () => {
  it('tracks document connections and server info', () => {
    const hooks: ConnectionRegistryHooks = {
      registerDocumentConnectionAuth: jest.fn(),
      unregisterDocumentConnectionAuth: jest.fn(() => 0),
      clearDocumentAuth: jest.fn(),
      clearDocumentCache: jest.fn(),
    };
    const registry = new ConnectionRegistry(hooks);

    registry.register({
      connection: buildConnection(),
      token: 'token-1',
      writeCapable: true,
    });
    registry.register({
      connection: buildConnection({ connectionId: 'conn-2', userId: 'user-2' }),
      token: 'token-2',
      writeCapable: false,
    });

    const info = registry.getServerInfo(8002, 12.5);
    expect(info.activeDocuments).toBe(1);
    expect(info.documents['doc-1']).toBe(2);
    expect(hooks.registerDocumentConnectionAuth).toHaveBeenCalledTimes(2);
  });

  it('supports disconnect fallback by user id and clears document state when empty', () => {
    const hooks: ConnectionRegistryHooks = {
      registerDocumentConnectionAuth: jest.fn(),
      unregisterDocumentConnectionAuth: jest.fn(() => 0),
      clearDocumentAuth: jest.fn(),
      clearDocumentCache: jest.fn(),
    };
    const registry = new ConnectionRegistry(hooks);

    registry.register({
      connection: buildConnection({ connectionId: 'conn-1', userId: 'user-1' }),
      token: 'token-1',
      writeCapable: true,
    });
    registry.register({
      connection: buildConnection({ connectionId: 'conn-2', userId: 'user-2' }),
      token: 'token-2',
      writeCapable: false,
    });

    expect(
      registry.unregister({
        documentId: 'doc-1',
        connectionId: 'missing-connection',
        userId: 'user-2',
      }),
    ).toBe(true);

    expect(hooks.unregisterDocumentConnectionAuth).toHaveBeenCalledWith('doc-1', 'conn-2');
    expect(hooks.clearDocumentAuth).not.toHaveBeenCalled();
    expect(hooks.clearDocumentCache).not.toHaveBeenCalled();

    expect(registry.unregister({ documentId: 'doc-1', connectionId: 'conn-1' })).toBe(true);
    expect(hooks.clearDocumentAuth).toHaveBeenCalledWith('doc-1');
    expect(hooks.clearDocumentCache).toHaveBeenCalledWith('doc-1');
  });
});
