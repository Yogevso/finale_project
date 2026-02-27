import axios, { AxiosError } from 'axios';
import type { DocumentStateTransportPort } from '../ports/documentStateTransportPort.js';

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

export class BackendDocumentStateTransportAdapter implements DocumentStateTransportPort {
  async loadDocumentState(documentId: string, token: string): Promise<Uint8Array | null> {
    try {
      const response = await axios.get(buildDocumentStateUrl(documentId), {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        responseType: 'arraybuffer',
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

  async saveDocumentState(documentId: string, state: Uint8Array, token: string): Promise<void> {
    await axios.put(buildDocumentStateUrl(documentId), state, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/octet-stream',
      },
    });
  }
}

