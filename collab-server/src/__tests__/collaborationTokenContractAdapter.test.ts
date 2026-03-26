import { CollaborationTokenContractAdapter } from '../adapters/collaborationTokenContractAdapter.js';
import { buildCollaborationTokenPayload } from './factories/collaborationFixtures.js';

describe('CollaborationTokenContractAdapter', () => {
  const adapter = new CollaborationTokenContractAdapter();

  it('maps valid collaboration payloads into auth context', () => {
    const result = adapter.mapDecodedToken(
      buildCollaborationTokenPayload({
        sub: '10',
        username: 'author',
        email: 'author@example.com',
        document_id: '55',
      }),
      '55',
    );

    expect(result.success).toBe(true);
    expect(result.user?.userId).toBe('10');
    expect(result.user?.traceId).toBe('trace-collab-123');
    expect(result.permissions).toEqual(['read', 'write']);
  });

  it('rejects token payloads for mismatched document ids', () => {
    const result = adapter.mapDecodedToken(
      buildCollaborationTokenPayload({
        sub: '10',
        username: 'author',
        email: 'author@example.com',
        document_id: '55',
        permissions: ['read'],
      }),
      '99',
    );

    expect(result.success).toBe(false);
    expect(result.error).toBe('Token is not valid for this document');
  });

  it('rejects malformed payloads', () => {
    const result = adapter.mapDecodedToken({ invalid: true }, '55');

    expect(result.success).toBe(false);
    expect(result.error).toBe('Invalid token');
  });
});
