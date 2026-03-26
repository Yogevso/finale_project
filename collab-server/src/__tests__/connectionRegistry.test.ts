import { ConnectionRegistry } from '../server/connectionRegistry.js';
import type { ConnectionRegistryHooks } from '../server/connectionRegistry.js';
import { jest } from '@jest/globals';
import { buildConnectionSetScenario } from './scenarios/collaborationScenario.js';

describe('ConnectionRegistry', () => {
  it('tracks document connections and server info', () => {
    const hooks: ConnectionRegistryHooks = {
      registerDocumentConnectionAuth: jest.fn(),
      unregisterDocumentConnectionAuth: jest.fn(() => 0),
      clearDocumentAuth: jest.fn(),
      clearDocumentCache: jest.fn(),
    };
    const registry = new ConnectionRegistry(hooks);
    const scenario = buildConnectionSetScenario('doc-1');

    registry.register({
      connection: scenario.writeConnection,
      token: 'token-1',
      writeCapable: true,
    });
    registry.register({
      connection: scenario.readConnection,
      token: 'token-2',
      writeCapable: false,
    });

    const info = registry.getServerInfo(8002, 12.5);
    expect(info.activeDocuments).toBe(1);
    expect(info.totalConnections).toBe(2);
    expect(info).not.toHaveProperty('documents');
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
    const scenario = buildConnectionSetScenario('doc-1');

    registry.register({
      connection: scenario.writeConnection,
      token: 'token-1',
      writeCapable: true,
    });
    registry.register({
      connection: scenario.readConnection,
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

  it('keeps the per-user connection index in sync for repeated fallback disconnects', () => {
    const hooks: ConnectionRegistryHooks = {
      registerDocumentConnectionAuth: jest.fn(),
      unregisterDocumentConnectionAuth: jest.fn(() => 0),
      clearDocumentAuth: jest.fn(),
      clearDocumentCache: jest.fn(),
    };
    const registry = new ConnectionRegistry(hooks);
    const scenario = buildConnectionSetScenario('doc-1');

    registry.register({
      connection: scenario.writeConnection,
      token: 'token-1',
      writeCapable: true,
    });
    registry.register({
      connection: {
        ...scenario.writeConnection,
        connectionId: 'conn-3',
      },
      token: 'token-3',
      writeCapable: true,
    });

    expect(registry.unregister({ documentId: 'doc-1', userId: 'user-1' })).toBe(true);
    expect(hooks.clearDocumentAuth).not.toHaveBeenCalled();
    expect(registry.unregister({ documentId: 'doc-1', userId: 'user-1' })).toBe(true);
    expect(hooks.clearDocumentAuth).toHaveBeenCalledWith('doc-1');
    expect(hooks.clearDocumentCache).toHaveBeenCalledWith('doc-1');
  });
});
