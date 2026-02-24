/**
 * Type definitions for the collaboration server
 */

export interface UserContext {
  userId: string;
  username: string;
  email: string;
  role: string;
  color: string;
}

export interface DocumentContext {
  documentId: string;
  documentName?: string;
}

export interface ConnectionContext extends UserContext, DocumentContext {
  connectionId: string;
  canWrite: boolean;
  connectedAt: Date;
}

export interface JWTPayload {
  sub: string;        // user id
  username: string;
  email: string;
  role: string;
  exp: number;
  iat: number;
}

export interface CollabTokenPayload extends JWTPayload {
  document_id: string;
  permissions: ('read' | 'write')[];
}

export interface PersistencePayload {
  documentId: string;
  state: Uint8Array;
  clientsCount: number;
}

export interface AwarenessUser {
  userId: string;
  username: string;
  color: string;
  cursor?: {
    anchor: number;
    head: number;
  };
}

// User colors for collaboration cursors
export const USER_COLORS = [
  '#F44336', // Red
  '#E91E63', // Pink
  '#9C27B0', // Purple
  '#673AB7', // Deep Purple
  '#3F51B5', // Indigo
  '#2196F3', // Blue
  '#03A9F4', // Light Blue
  '#00BCD4', // Cyan
  '#009688', // Teal
  '#4CAF50', // Green
  '#8BC34A', // Light Green
  '#CDDC39', // Lime
  '#FFC107', // Amber
  '#FF9800', // Orange
  '#FF5722', // Deep Orange
];

export function getUserColor(userId: string): string {
  // Generate consistent color based on user ID
  let hash = 0;
  for (let i = 0; i < userId.length; i++) {
    hash = userId.charCodeAt(i) + ((hash << 5) - hash);
  }
  return USER_COLORS[Math.abs(hash) % USER_COLORS.length];
}
