/**
 * JWT Authentication for Hocuspocus
 * Validates collaboration tokens issued by FastAPI backend
 */

import jwt from 'jsonwebtoken';
import type { CollabTokenPayload, UserContext } from './types.js';
import { getUserColor } from './types.js';

const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key-change-in-production';

export interface AuthResult {
  success: boolean;
  user?: UserContext;
  permissions?: ('read' | 'write')[];
  error?: string;
}

/**
 * Verify a collaboration token and extract user info
 */
export function verifyCollabToken(token: string, documentId: string): AuthResult {
  try {
    const decoded = jwt.verify(token, JWT_SECRET) as CollabTokenPayload;
    
    // Verify the token is for the correct document
    if (decoded.document_id !== documentId) {
      return {
        success: false,
        error: 'Token is not valid for this document',
      };
    }

    return {
      success: true,
      user: {
        userId: decoded.sub,
        username: decoded.username,
        email: decoded.email,
        role: decoded.role,
        color: getUserColor(decoded.sub),
      },
      permissions: decoded.permissions,
    };
  } catch (error) {
    if (error instanceof jwt.TokenExpiredError) {
      return {
        success: false,
        error: 'Token has expired',
      };
    }
    if (error instanceof jwt.JsonWebTokenError) {
      return {
        success: false,
        error: 'Invalid token',
      };
    }
    return {
      success: false,
      error: 'Authentication failed',
    };
  }
}

/**
 * Check if user has write permission
 */
export function canWrite(permissions: ('read' | 'write')[]): boolean {
  return permissions.includes('write');
}

/**
 * Check if user has read permission
 */
export function canRead(permissions: ('read' | 'write')[]): boolean {
  return permissions.includes('read') || permissions.includes('write');
}

/**
 * Extract token from WebSocket URL query params or headers
 */
export function extractToken(requestParameters: URLSearchParams): string | null {
  return requestParameters.get('token');
}

/**
 * Extract document ID from WebSocket URL
 * URL format: ws://localhost:8002/document/{documentId}
 */
export function extractDocumentId(documentName: string): string {
  // The documentName in Hocuspocus is the path after the base URL
  // e.g., "document/123" -> "123"
  const parts = documentName.split('/');
  return parts[parts.length - 1];
}
