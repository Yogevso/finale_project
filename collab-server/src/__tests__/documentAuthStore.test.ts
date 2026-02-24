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

describe('documentAuthStore', () => {
  const documentId = 'doc-123';

  beforeEach(() => {
    clearDocumentAuth(documentId);
  });

  afterEach(() => {
    clearDocumentAuth(documentId);
  });

  it('keeps write token stable when read-only users connect later', () => {
    registerDocumentConnectionAuth({
      documentId,
      connectionId: 'conn-write',
      token: 'token-write',
      writeCapable: true,
    });
    registerDocumentConnectionAuth({
      documentId,
      connectionId: 'conn-read',
      token: 'token-read',
      writeCapable: false,
    });

    expect(getDocumentTokenForStore(documentId)).toBe('token-write');
    expect(getDocumentTokenForLoad(documentId)).toBe('token-write');
  });

  it('falls back to read token for load when no write-capable connection exists', () => {
    registerDocumentConnectionAuth({
      documentId,
      connectionId: 'conn-read',
      token: 'token-read',
      writeCapable: false,
    });

    expect(getDocumentTokenForStore(documentId)).toBeNull();
    expect(getDocumentTokenForLoad(documentId)).toBe('token-read');
  });

  it('does not clear remaining connection tokens when one connection disconnects', () => {
    registerDocumentConnectionAuth({
      documentId,
      connectionId: 'conn-a',
      token: 'token-a',
      writeCapable: true,
    });
    registerDocumentConnectionAuth({
      documentId,
      connectionId: 'conn-b',
      token: 'token-b',
      writeCapable: false,
    });

    const remaining = unregisterDocumentConnectionAuth(documentId, 'conn-a');
    expect(remaining).toBe(1);
    expect(getDocumentTokenForLoad(documentId)).toBe('token-b');
    expect(getDocumentAuthStats(documentId).connections).toBe(1);
  });

  it('cleans up state after the last connection disconnects', () => {
    const trackedBefore = getTrackedDocumentCount();
    registerDocumentConnectionAuth({
      documentId,
      connectionId: 'conn-a',
      token: 'token-a',
      writeCapable: true,
    });

    expect(getTrackedDocumentCount()).toBe(trackedBefore + 1);
    const remaining = unregisterDocumentConnectionAuth(documentId, 'conn-a');
    expect(remaining).toBe(0);
    expect(getTrackedDocumentCount()).toBe(trackedBefore);
    expect(getDocumentTokenForLoad(documentId)).toBeNull();
    expect(getDocumentTokenForStore(documentId)).toBeNull();
  });
});
