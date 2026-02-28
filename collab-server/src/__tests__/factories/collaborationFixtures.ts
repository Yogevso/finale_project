import jwt from 'jsonwebtoken';

import type { CollaborationTokenContract } from '../../authContext/contracts.js';
import type { ConnectionContext } from '../../types.js';

export function buildCollaborationTokenPayload(
  overrides: Partial<CollaborationTokenContract> = {},
): CollaborationTokenContract {
  const nowSeconds = Math.floor(Date.now() / 1000);
  return {
    sub: '1',
    username: 'testuser',
    email: 'test@example.com',
    role: 'editor',
    document_id: '123',
    permissions: ['read', 'write'],
    exp: nowSeconds + 3600,
    iat: nowSeconds,
    type: 'collaboration',
    ...overrides,
  };
}

export function signCollaborationToken(
  overrides: Partial<CollaborationTokenContract> = {},
  secret: string = 'your-secret-key-change-in-production',
): string {
  return jwt.sign(buildCollaborationTokenPayload(overrides), secret);
}

export function buildConnectionContext(
  overrides: Partial<ConnectionContext> = {},
): ConnectionContext {
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

export function buildDocumentConnectionAuth(
  overrides: Partial<{
    documentId: string;
    connectionId: string;
    token: string;
    writeCapable: boolean;
  }> = {},
): {
  documentId: string;
  connectionId: string;
  token: string;
  writeCapable: boolean;
} {
  return {
    documentId: 'doc-123',
    connectionId: 'conn-a',
    token: 'token-a',
    writeCapable: true,
    ...overrides,
  };
}
