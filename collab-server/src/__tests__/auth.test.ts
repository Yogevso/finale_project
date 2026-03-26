/**
 * Unit Tests for Collaboration Server Authentication
 */

import {
  verifyCollabToken,
  canWrite,
  canRead,
  extractToken,
  extractDocumentId,
} from '../auth.js';
import {
  CollaborationAuthService,
  resolveCollaborationJwtSecret,
  resolveCollaborationJwtVerificationSecrets,
} from '../authContext/collaborationAuthService.js';
import { signCollaborationToken } from './factories/collaborationFixtures.js';

const SHARED_SECRET = process.env.SECRET_KEY || process.env.JWT_SECRET || 'your-secret-key-change-in-production';
process.env.SECRET_KEY = process.env.SECRET_KEY || SHARED_SECRET;

describe('Authentication', () => {
  describe('resolveCollaborationJwtSecret', () => {
    it('prefers SECRET_KEY over JWT_SECRET when both are present', () => {
      expect(
        resolveCollaborationJwtSecret({
          SECRET_KEY: 'shared-secret-material-1234567890',
          JWT_SECRET: 'legacy-secret-material-1234567890',
        }),
      ).toBe('shared-secret-material-1234567890');
    });

    it('falls back to JWT_SECRET for legacy environments', () => {
      expect(
        resolveCollaborationJwtSecret({
          JWT_SECRET: 'legacy-secret-material-1234567890',
        }),
      ).toBe('legacy-secret-material-1234567890');
    });

    it('includes SECRET_KEY_OLD for verification during rotation', () => {
      expect(
        resolveCollaborationJwtVerificationSecrets({
          SECRET_KEY: 'shared-secret-material-1234567890',
          SECRET_KEY_OLD: 'old-secret-material-1234567890123',
        }),
      ).toEqual([
        'shared-secret-material-1234567890',
        'old-secret-material-1234567890123',
      ]);
    });
  });

  describe('verifyCollabToken', () => {
    it('should verify a valid token', () => {
      const token = signCollaborationToken({}, SHARED_SECRET);

      const result = verifyCollabToken(token, '123');

      expect(result.success).toBe(true);
      expect(result.user).toBeDefined();
      expect(result.user?.userId).toBe('1');
      expect(result.user?.username).toBe('testuser');
      expect(result.user?.traceId).toBe('trace-collab-123');
      expect(result.permissions).toEqual(['read', 'write']);
    });

    it('should reject token for wrong document', () => {
      const token = signCollaborationToken({}, SHARED_SECRET);

      const result = verifyCollabToken(token, '456');

      expect(result.success).toBe(false);
      expect(result.error).toBe('Token is not valid for this document');
    });

    it('should reject expired token', () => {
      const nowSeconds = Math.floor(Date.now() / 1000);
      const token = signCollaborationToken(
        {
          exp: nowSeconds - 3600,
          iat: nowSeconds - 7200,
        },
        SHARED_SECRET,
      );

      const result = verifyCollabToken(token, '123');

      expect(result.success).toBe(false);
      expect(result.error).toBe('Token has expired');
    });

    it('should reject invalid token', () => {
      const result = verifyCollabToken('invalid-token', '123');

      expect(result.success).toBe(false);
      expect(result.error).toBe('Invalid token');
    });

    it('should reject token signed with wrong secret', () => {
      const token = signCollaborationToken({}, 'wrong-secret');

      const result = verifyCollabToken(token, '123');

      expect(result.success).toBe(false);
      expect(result.error).toBe('Invalid token');
    });

    it('should reject token with non-collaboration type', () => {
      const token = signCollaborationToken({ type: 'access' }, SHARED_SECRET);

      const result = verifyCollabToken(token, '123');

      expect(result.success).toBe(false);
      expect(result.error).toBe('Invalid token');
    });

    it('should accept token signed with SECRET_KEY_OLD during rotation', () => {
      const oldSecret = 'old-shared-secret-material-1234567890';
      const token = signCollaborationToken({}, oldSecret);
      const authService = new CollaborationAuthService([SHARED_SECRET, oldSecret]);

      const result = authService.verifyCollabToken(token, '123');

      expect(result.success).toBe(true);
    });

    it('should assign consistent user colors', () => {
      const token = signCollaborationToken(
        {
          sub: '42',
          username: 'coloruser',
          email: 'color@example.com',
          permissions: ['read'],
        },
        SHARED_SECRET,
      );

      const result1 = verifyCollabToken(token, '123');
      const result2 = verifyCollabToken(token, '123');

      expect(result1.user?.color).toBe(result2.user?.color);
    });
  });

  describe('Permission Checks', () => {
    it('canWrite should return true for write permission', () => {
      expect(canWrite(['read', 'write'])).toBe(true);
    });

    it('canWrite should return false for read-only', () => {
      expect(canWrite(['read'])).toBe(false);
    });

    it('canRead should return true for read permission', () => {
      expect(canRead(['read'])).toBe(true);
    });

    it('canRead should return true for write permission', () => {
      expect(canRead(['write'])).toBe(true);
    });

    it('canRead should return false for empty permissions', () => {
      expect(canRead([])).toBe(false);
    });
  });

  describe('Token Extraction', () => {
    it('should extract token from URL params', () => {
      const params = new URLSearchParams('token=abc123&other=value');
      expect(extractToken(params)).toBe('abc123');
    });

    it('should return null if no token in params', () => {
      const params = new URLSearchParams('other=value');
      expect(extractToken(params)).toBeNull();
    });
  });

  describe('Document ID Extraction', () => {
    it('should extract document ID from path', () => {
      expect(extractDocumentId('document/123')).toBe('123');
    });

    it('should handle nested paths', () => {
      expect(extractDocumentId('prefix/document/456')).toBe('456');
    });

    it('should handle simple ID', () => {
      expect(extractDocumentId('789')).toBe('789');
    });
  });
});
