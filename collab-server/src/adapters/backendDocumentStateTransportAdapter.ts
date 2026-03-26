import axios, { AxiosError } from 'axios';
import type { DocumentStateTransportPort } from '../ports/documentStateTransportPort.js';
import { buildTraceHeaders } from '../trace.js';

export function normalizeApiPrefix(prefix: string): string {
  if (!prefix) {
    return '';
  }
  const withLeadingSlash = prefix.startsWith('/') ? prefix : `/${prefix}`;
  return withLeadingSlash.replace(/\/+$/, '');
}

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const BACKEND_API_PREFIX = normalizeApiPrefix(process.env.BACKEND_API_PREFIX || '/api/v1');
const COLLAB_STATE_PATH = '/collaboration/documents';

export function buildDocumentStateUrl(
  documentId: string,
  options?: {
    backendUrl?: string;
    apiPrefix?: string;
  }
): string {
  const backendUrl = (options?.backendUrl ?? BACKEND_URL).replace(/\/+$/, '');
  const apiPrefix = normalizeApiPrefix(options?.apiPrefix ?? BACKEND_API_PREFIX);
  return `${backendUrl}${apiPrefix}${COLLAB_STATE_PATH}/${documentId}/state`;
}

// H-12: 10-second timeout for backend HTTP requests
const BACKEND_TIMEOUT_MS = 10_000;

export class BackendDocumentStateTransportAdapter implements DocumentStateTransportPort {
  async loadDocumentState(
    documentId: string,
    token: string,
    traceId?: string,
  ): Promise<Uint8Array | null> {
    try {
      const response = await axios.get(buildDocumentStateUrl(documentId), {
        headers: {
          Authorization: `Bearer ${token}`,
          ...buildTraceHeaders(traceId),
        },
        responseType: 'arraybuffer',
        timeout: BACKEND_TIMEOUT_MS,
      });

      if (response.status !== 200 || !response.data) {
        return null;
      }
      return new Uint8Array(response.data);
    } catch (error) {
      if (error instanceof AxiosError && error.response?.status === 404) {
        return null;
      }
      throw error;
    }
  }

  async saveDocumentState(
    documentId: string,
    state: Uint8Array,
    token: string,
    traceId?: string,
  ): Promise<void> {
    await axios.put(buildDocumentStateUrl(documentId), state, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/octet-stream',
        ...buildTraceHeaders(traceId),
      },
      timeout: BACKEND_TIMEOUT_MS,
    });
  }
}
