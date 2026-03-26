/**
 * Unit tests for per-document auth token tracking.
 */

import {
  clearDocumentAuth,
  getDocumentAuthStats,
  getDocumentTokenForLoad,
  getDocumentTokenForStore,
  getTrackedDocumentCount,
  registerDocumentConnectionAuth,
  unregisterDocumentConnectionAuth,
} from '../documentAuthStore.js';
import { buildDocumentConnectionAuth } from './factories/collaborationFixtures.js';
import { buildConnectionSetScenario } from './scenarios/collaborationScenario.js';
import { signCollaborationToken } from './factories/collaborationFixtures.js';

describe('documentAuthStore', () => {
  const documentId = 'doc-123';
  const otherDocumentId = 'doc-456';

  beforeEach(() => {
    clearDocumentAuth(documentId);
    clearDocumentAuth(otherDocumentId);
  });

  afterEach(() => {
    clearDocumentAuth(documentId);
    clearDocumentAuth(otherDocumentId);
  });

  it('keeps write token stable when read-only users connect later', () => {
    const scenario = buildConnectionSetScenario(documentId);
    registerDocumentConnectionAuth(
      buildDocumentConnectionAuth({
        ...scenario.writeAuth,
        connectionId: 'conn-write',
        token: signCollaborationToken({ document_id: documentId }),
      }),
    );
    registerDocumentConnectionAuth(
      buildDocumentConnectionAuth({
        ...scenario.readAuth,
        connectionId: 'conn-read',
        token: signCollaborationToken({
          sub: '2',
          username: 'readonly',
          email: 'readonly@example.com',
          permissions: ['read'],
          document_id: documentId,
        }),
      }),
    );

    const storedWriteToken = getDocumentTokenForStore(documentId);
    expect(storedWriteToken).not.toBeNull();
    expect(getDocumentTokenForLoad(documentId)).toBe(storedWriteToken);
  });

  it('falls back to read token for load when no write-capable connection exists', () => {
    const scenario = buildConnectionSetScenario(documentId);
    const readToken = signCollaborationToken({
      sub: '2',
      username: 'readonly',
      email: 'readonly@example.com',
      permissions: ['read'],
      document_id: documentId,
    });
    registerDocumentConnectionAuth(
      buildDocumentConnectionAuth({
        ...scenario.readAuth,
        connectionId: 'conn-read',
        token: readToken,
      }),
    );

    expect(getDocumentTokenForStore(documentId)).toBeNull();
    expect(getDocumentTokenForLoad(documentId)).toBe(readToken);
  });

  it('does not clear remaining connection tokens when one connection disconnects', () => {
    const scenario = buildConnectionSetScenario(documentId);
    const tokenA = signCollaborationToken({ document_id: documentId });
    const tokenB = signCollaborationToken({
      sub: '2',
      username: 'readonly',
      email: 'readonly@example.com',
      permissions: ['read'],
      document_id: documentId,
    });
    registerDocumentConnectionAuth(
      buildDocumentConnectionAuth({
        ...scenario.writeAuth,
        connectionId: 'conn-a',
        token: tokenA,
      }),
    );
    registerDocumentConnectionAuth(
      buildDocumentConnectionAuth({
        ...scenario.readAuth,
        connectionId: 'conn-b',
        token: tokenB,
      }),
    );

    const remaining = unregisterDocumentConnectionAuth(documentId, 'conn-a');
    expect(remaining).toBe(1);
    expect(getDocumentTokenForLoad(documentId)).toBe(tokenB);
    expect(getDocumentAuthStats(documentId).connections).toBe(1);
  });

  it('cleans up state after the last connection disconnects', () => {
    const trackedBefore = getTrackedDocumentCount();
    const scenario = buildConnectionSetScenario(documentId);
    registerDocumentConnectionAuth(
      buildDocumentConnectionAuth({
        ...scenario.writeAuth,
        connectionId: 'conn-a',
        token: signCollaborationToken({ document_id: documentId }),
      }),
    );

    expect(getTrackedDocumentCount()).toBe(trackedBefore + 1);
    const remaining = unregisterDocumentConnectionAuth(documentId, 'conn-a');
    expect(remaining).toBe(0);
    expect(getTrackedDocumentCount()).toBe(trackedBefore);
    expect(getDocumentTokenForLoad(documentId)).toBeNull();
    expect(getDocumentTokenForStore(documentId)).toBeNull();
  });

  it('rejects tokens whose document claim does not match the tracked document', () => {
    expect(() =>
      registerDocumentConnectionAuth(
        buildDocumentConnectionAuth({
          documentId,
          connectionId: 'conn-mismatch',
          token: signCollaborationToken({ document_id: otherDocumentId }),
          writeCapable: true,
        }),
      ),
    ).toThrow('Token is not valid for this document');

    expect(getDocumentTokenForLoad(documentId)).toBeNull();
    expect(getDocumentTokenForStore(documentId)).toBeNull();
    expect(getDocumentAuthStats(documentId)).toEqual({
      connections: 0,
      writeConnections: 0,
    });
  });
});
