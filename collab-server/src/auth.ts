/**
 * JWT Authentication for Hocuspocus
 * Validates collaboration tokens issued by FastAPI backend
 */

import {
  CollaborationAuthService,
  type AuthResult,
} from './authContext/collaborationAuthService.js';
import type { CollaborationPermission } from './authContext/contracts.js';

const collabAuthService = new CollaborationAuthService();

/**
 * Verify a collaboration token and extract user info
 */
export function verifyCollabToken(token: string, documentId: string): AuthResult {
  return collabAuthService.verifyCollabToken(token, documentId);
}

/**
 * Check if user has write permission
 */
export function canWrite(permissions: CollaborationPermission[]): boolean {
  return collabAuthService.canWrite(permissions);
}

/**
 * Check if user has read permission
 */
export function canRead(permissions: CollaborationPermission[]): boolean {
  return collabAuthService.canRead(permissions);
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
  const id = parts[parts.length - 1];
  if (!/^\d+$/.test(id)) {
    throw new Error(`Invalid document ID: ${id}`);
  }
  return id;
}
