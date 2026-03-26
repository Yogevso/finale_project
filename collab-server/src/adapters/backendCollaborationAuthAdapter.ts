import axios, { AxiosError } from 'axios';

import type { CollaborationPermission } from '../authContext/contracts.js';
import { buildTraceHeaders } from '../trace.js';
import { normalizeApiPrefix } from './backendDocumentStateTransportAdapter.js';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const BACKEND_API_PREFIX = normalizeApiPrefix(process.env.BACKEND_API_PREFIX || '/api/v1');
const COLLAB_VERIFY_PATH = '/collaboration/documents';
const BACKEND_TIMEOUT_MS = 10_000;

export interface VerifyCollaborationAccessResult {
  success: boolean;
  permissions?: CollaborationPermission[];
  error?: string;
}

export function buildCollaborationVerifyAccessUrl(
  documentId: string,
  options?: {
    backendUrl?: string;
    apiPrefix?: string;
  },
): string {
  const backendUrl = (options?.backendUrl ?? BACKEND_URL).replace(/\/+$/, '');
  const apiPrefix = normalizeApiPrefix(options?.apiPrefix ?? BACKEND_API_PREFIX);
  return `${backendUrl}${apiPrefix}${COLLAB_VERIFY_PATH}/${documentId}/verify-access`;
}

export async function verifyCollaborationAccess(
  documentId: string,
  token: string,
  traceId?: string,
): Promise<VerifyCollaborationAccessResult> {
  try {
    const response = await axios.get(buildCollaborationVerifyAccessUrl(documentId), {
      headers: {
        Authorization: `Bearer ${token}`,
        ...buildTraceHeaders(traceId),
      },
      timeout: BACKEND_TIMEOUT_MS,
    });

    return {
      success: true,
      permissions: response.data?.permissions,
    };
  } catch (error) {
    if (error instanceof AxiosError) {
      const detail =
        typeof error.response?.data?.detail === 'string'
          ? error.response.data.detail
          : undefined;
      if (
        error.response?.status === 401 ||
        error.response?.status === 403 ||
        error.response?.status === 404
      ) {
        return {
          success: false,
          error: detail || 'Authentication failed',
        };
      }
    }
    throw error;
  }
}
