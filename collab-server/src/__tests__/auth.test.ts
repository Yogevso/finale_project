/**
 * Unit Tests for Collaboration Server Authentication
 */

import jwt from 'jsonwebtoken';
import {
  verifyCollabToken,
  canWrite,
  canRead,
  extractToken,
  extractDocumentId,
} from '../auth.js';

const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key-change-in-production';

describe('Authentication', () => {
  // Helper to create a valid token
  const createTestToken = (payload: Record<string, unknown>, secret = JWT_SECRET) => {
    return jwt.sign(payload, secret);
  };

  describe('verifyCollabToken', () => {
    it('should verify a valid token', () => {
      const token = createTestToken({
        sub: '1',
        username: 'testuser',
        email: 'test@example.com',
        role: 'editor',
        document_id: '123',
        permissions: ['read', 'write'],
        exp: Math.floor(Date.now() / 1000) + 3600,
        iat: Math.floor(Date.now() / 1000),
      });

      const result = verifyCollabToken(token, '123');

      expect(result.success).toBe(true);
      expect(result.user).toBeDefined();
      expect(result.user?.userId).toBe('1');
      expect(result.user?.username).toBe('testuser');
      expect(result.permissions).toEqual(['read', 'write']);
    });

    it('should reject token for wrong document', () => {
      const token = createTestToken({
        sub: '1',
        username: 'testuser',
        email: 'test@example.com',
        role: 'editor',
        document_id: '123',
        permissions: ['read', 'write'],
        exp: Math.floor(Date.now() / 1000) + 3600,
        iat: Math.floor(Date.now() / 1000),
      });

      const result = verifyCollabToken(token, '456');

      expect(result.success).toBe(false);
      expect(result.error).toBe('Token is not valid for this document');
    });

    it('should reject expired token', () => {
      const token = createTestToken({
        sub: '1',
        username: 'testuser',
        email: 'test@example.com',
        role: 'editor',
        document_id: '123',
        permissions: ['read', 'write'],
        exp: Math.floor(Date.now() / 1000) - 3600, // Expired 1 hour ago
        iat: Math.floor(Date.now() / 1000) - 7200,
      });

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
      const token = createTestToken(
        {
          sub: '1',
          username: 'testuser',
          email: 'test@example.com',
          role: 'editor',
          document_id: '123',
          permissions: ['read', 'write'],
          exp: Math.floor(Date.now() / 1000) + 3600,
          iat: Math.floor(Date.now() / 1000),
        },
        'wrong-secret'
      );

      const result = verifyCollabToken(token, '123');

      expect(result.success).toBe(false);
      expect(result.error).toBe('Invalid token');
    });

    it('should reject token with non-collaboration type', () => {
      const token = createTestToken({
        sub: '1',
        username: 'testuser',
        email: 'test@example.com',
        role: 'editor',
        document_id: '123',
        permissions: ['read', 'write'],
        type: 'access',
        exp: Math.floor(Date.now() / 1000) + 3600,
        iat: Math.floor(Date.now() / 1000),
      });

      const result = verifyCollabToken(token, '123');

      expect(result.success).toBe(false);
      expect(result.error).toBe('Invalid token');
    });

    it('should assign consistent user colors', () => {
      const token = createTestToken({
        sub: '42',
        username: 'coloruser',
        email: 'color@example.com',
        role: 'editor',
        document_id: '123',
        permissions: ['read'],
        exp: Math.floor(Date.now() / 1000) + 3600,
        iat: Math.floor(Date.now() / 1000),
      });

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
