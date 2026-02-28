/**
 * Unit tests for persistence URL composition and resilience behavior.
 */

import { jest } from '@jest/globals';

import type { DocumentStateTransportPort } from '../ports/documentStateTransportPort.js';
import {
  buildDocumentStateUrl,
  clearDocumentCache,
  getCacheStats,
  loadDocument,
  saveDocument,
} from '../persistence.js';

function clearAllCachedDocuments(): void {
  const { documents } = getCacheStats();
  for (const documentId of documents) {
    clearDocumentCache(documentId);
  }
}

describe('Persistence URL composition', () => {
  it('uses /api/v1 by default and normalizes trailing slashes', () => {
    expect(buildDocumentStateUrl('123')).toBe(
      'http://localhost:8000/api/v1/collaboration/documents/123/state',
    );
  });

  it('supports custom API prefix with or without leading slash', () => {
    expect(
      buildDocumentStateUrl('abc', {
        backendUrl: 'http://backend:8000',
        apiPrefix: 'api/custom/',
      }),
    ).toBe(
      'http://backend:8000/api/custom/collaboration/documents/abc/state',
    );
  });
});

describe('Persistence resilience behavior', () => {
  beforeEach(() => {
    clearAllCachedDocuments();
  });

  afterEach(() => {
    clearAllCachedDocuments();
  });

  it('returns null when load transport times out', async () => {
    const transport: DocumentStateTransportPort = {
      loadDocumentState: jest.fn(async () => {
        throw new Error('backend timeout');
      }),
      saveDocumentState: jest.fn(async () => undefined),
    };

    const loaded = await loadDocument('timeout-doc', 'token', transport);

    expect(loaded).toBeNull();
    expect(getCacheStats().documents).not.toContain('timeout-doc');
  });

  it('treats malformed upstream state payloads as missing state', async () => {
    const transport: DocumentStateTransportPort = {
      loadDocumentState: jest.fn(async () => 'not-binary-state' as unknown as Uint8Array),
      saveDocumentState: jest.fn(async () => undefined),
    };

    const loaded = await loadDocument('malformed-doc', 'token', transport);

    expect(loaded).toBeNull();
    expect(getCacheStats().documents).not.toContain('malformed-doc');
  });

  it('keeps a local cache fallback when save partially fails', async () => {
    const state = new Uint8Array([1, 2, 3, 4]);
    const transport: DocumentStateTransportPort = {
      loadDocumentState: jest.fn(async () => new Uint8Array([9, 9, 9])),
      saveDocumentState: jest.fn(async () => {
        throw new Error('backend timeout');
      }),
    };

    const saveResult = await saveDocument('partial-failure-doc', state, 'token', transport);
    const loadedAfterFailure = await loadDocument('partial-failure-doc', 'token', transport);

    expect(saveResult).toEqual({ success: false, error: 'backend timeout' });
    expect(loadedAfterFailure).toEqual(state);
    expect((transport.loadDocumentState as jest.Mock).mock.calls).toHaveLength(0);
  });

  it('reports repeated save failures without throwing after retries are exhausted', async () => {
    const state = new Uint8Array([5, 6, 7]);
    const transport: DocumentStateTransportPort = {
      loadDocumentState: jest.fn(async () => null),
      saveDocumentState: jest.fn(async () => {
        throw new Error('transport timeout');
      }),
    };

    const first = await saveDocument('retry-exhausted-doc', state, 'token', transport);
    const second = await saveDocument('retry-exhausted-doc', state, 'token', transport);
    const third = await saveDocument('retry-exhausted-doc', state, 'token', transport);

    expect(first).toEqual({ success: false, error: 'transport timeout' });
    expect(second).toEqual({ success: false, error: 'transport timeout' });
    expect(third).toEqual({ success: false, error: 'transport timeout' });
    expect((transport.saveDocumentState as jest.Mock).mock.calls).toHaveLength(3);
  });
});
