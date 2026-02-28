import type { CollabTokenPayload } from '../types.js';

export const COLLAB_TOKEN_TYPE = 'collaboration';
export type CollaborationPermission = 'read' | 'write';

export interface CollaborationTokenContract extends CollabTokenPayload {
  type?: string;
}

const ALLOWED_PERMISSIONS = new Set<CollaborationPermission>(['read', 'write']);

function isString(value: unknown): value is string {
  return typeof value === 'string';
}

export function isPermissionList(value: unknown): value is CollaborationPermission[] {
  if (!Array.isArray(value)) {
    return false;
  }

  return value.every(
    (permission) =>
      typeof permission === 'string' &&
      ALLOWED_PERMISSIONS.has(permission as CollaborationPermission),
  );
}

export function isCollaborationTokenContract(
  payload: unknown,
): payload is CollaborationTokenContract {
  if (!payload || typeof payload !== 'object') {
    return false;
  }

  const candidate = payload as Record<string, unknown>;
  if (
    !isString(candidate.sub) ||
    !isString(candidate.username) ||
    !isString(candidate.email) ||
    !isString(candidate.role) ||
    !isString(candidate.document_id) ||
    !isPermissionList(candidate.permissions)
  ) {
    return false;
  }

  if (candidate.type !== undefined && !isString(candidate.type)) {
    return false;
  }

  return true;
}
