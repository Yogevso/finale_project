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

describe('documentAuthStore', () => {
  const documentId = 'doc-123';

  beforeEach(() => {
    clearDocumentAuth(documentId);
  });

  afterEach(() => {
    clearDocumentAuth(documentId);
  });

  it('keeps write token stable when read-only users connect later', () => {
    const scenario = buildConnectionSetScenario(documentId);
    registerDocumentConnectionAuth(
      buildDocumentConnectionAuth({
        ...scenario.writeAuth,
        connectionId: 'conn-write',
        token: 'token-write',
      }),
    );
    registerDocumentConnectionAuth(
      buildDocumentConnectionAuth({
        ...scenario.readAuth,
        connectionId: 'conn-read',
        token: 'token-read',
      }),
    );

    expect(getDocumentTokenForStore(documentId)).toBe('token-write');
    expect(getDocumentTokenForLoad(documentId)).toBe('token-write');
  });

  it('falls back to read token for load when no write-capable connection exists', () => {
    const scenario = buildConnectionSetScenario(documentId);
    registerDocumentConnectionAuth(
      buildDocumentConnectionAuth({
        ...scenario.readAuth,
        connectionId: 'conn-read',
        token: 'token-read',
      }),
    );

    expect(getDocumentTokenForStore(documentId)).toBeNull();
    expect(getDocumentTokenForLoad(documentId)).toBe('token-read');
  });

  it('does not clear remaining connection tokens when one connection disconnects', () => {
    const scenario = buildConnectionSetScenario(documentId);
    registerDocumentConnectionAuth(
      buildDocumentConnectionAuth({
        ...scenario.writeAuth,
        connectionId: 'conn-a',
        token: 'token-a',
      }),
    );
    registerDocumentConnectionAuth(
      buildDocumentConnectionAuth({
        ...scenario.readAuth,
        connectionId: 'conn-b',
        token: 'token-b',
      }),
    );

    const remaining = unregisterDocumentConnectionAuth(documentId, 'conn-a');
    expect(remaining).toBe(1);
    expect(getDocumentTokenForLoad(documentId)).toBe('token-b');
    expect(getDocumentAuthStats(documentId).connections).toBe(1);
  });

  it('cleans up state after the last connection disconnects', () => {
    const trackedBefore = getTrackedDocumentCount();
    const scenario = buildConnectionSetScenario(documentId);
    registerDocumentConnectionAuth(
      buildDocumentConnectionAuth({
        ...scenario.writeAuth,
        connectionId: 'conn-a',
        token: 'token-a',
      }),
    );

    expect(getTrackedDocumentCount()).toBe(trackedBefore + 1);
    const remaining = unregisterDocumentConnectionAuth(documentId, 'conn-a');
    expect(remaining).toBe(0);
    expect(getTrackedDocumentCount()).toBe(trackedBefore);
    expect(getDocumentTokenForLoad(documentId)).toBeNull();
    expect(getDocumentTokenForStore(documentId)).toBeNull();
  });
});
