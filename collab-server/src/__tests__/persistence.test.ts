/**
 * Unit tests for persistence URL composition.
 */

import { buildDocumentStateUrl } from '../persistence.js';

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
