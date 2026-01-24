/**
 * Document Persistence for Hocuspocus
 * Saves Yjs state to FastAPI backend
 */

import axios, { AxiosError } from 'axios';
import * as Y from 'yjs';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// In-memory cache for document states (for quick access)
const documentCache = new Map<string, Uint8Array>();

export interface PersistenceResult {
  success: boolean;
  error?: string;
}

/**
 * Load document state from FastAPI backend
 */
export async function loadDocument(
  documentId: string,
  token: string
): Promise<Uint8Array | null> {
  // Check cache first
  const cached = documentCache.get(documentId);
  if (cached) {
    console.log(`[Persistence] Loaded document ${documentId} from cache`);
    return cached;
  }

  try {
    const response = await axios.get(
      `${BACKEND_URL}/api/management/collaboration/documents/${documentId}/state`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        responseType: 'arraybuffer',
      }
    );

    if (response.status === 200 && response.data) {
      const state = new Uint8Array(response.data);
      documentCache.set(documentId, state);
      console.log(`[Persistence] Loaded document ${documentId} from backend (${state.length} bytes)`);
      return state;
    }

    return null;
  } catch (error) {
    if (error instanceof AxiosError && error.response?.status === 404) {
      // Document exists but has no Yjs state yet - this is fine
      console.log(`[Persistence] Document ${documentId} has no existing state`);
      return null;
    }
    console.error(`[Persistence] Failed to load document ${documentId}:`, error);
    return null;
  }
}

/**
 * Save document state to FastAPI backend
 */
export async function saveDocument(
  documentId: string,
  state: Uint8Array,
  token: string
): Promise<PersistenceResult> {
  // Update cache
  documentCache.set(documentId, state);

  try {
    await axios.put(
      `${BACKEND_URL}/api/management/collaboration/documents/${documentId}/state`,
      state,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/octet-stream',
        },
      }
    );

    console.log(`[Persistence] Saved document ${documentId} to backend (${state.length} bytes)`);
    return { success: true };
  } catch (error) {
    console.error(`[Persistence] Failed to save document ${documentId}:`, error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Convert Yjs document to HTML for display/search
 */
export function yjsToHtml(ydoc: Y.Doc): string {
  // Get the XML fragment from TipTap's default structure
  const xmlFragment = ydoc.getXmlFragment('default');
  return xmlFragmentToHtml(xmlFragment);
}

/**
 * Convert XML fragment to HTML string
 */
function xmlFragmentToHtml(fragment: Y.XmlFragment): string {
  let html = '';
  
  fragment.forEach((item) => {
    if (item instanceof Y.XmlText) {
      html += escapeHtml(item.toString());
    } else if (item instanceof Y.XmlElement) {
      const tagName = item.nodeName;
      const attrs = item.getAttributes();
      
      let attrString = '';
      for (const [key, value] of Object.entries(attrs)) {
        attrString += ` ${key}="${escapeHtml(String(value))}"`;
      }
      
      html += `<${tagName}${attrString}>`;
      html += xmlFragmentToHtml(item);
      html += `</${tagName}>`;
    }
  });
  
  return html;
}

/**
 * Escape HTML special characters
 */
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * Clear document from cache
 */
export function clearDocumentCache(documentId: string): void {
  documentCache.delete(documentId);
  console.log(`[Persistence] Cleared cache for document ${documentId}`);
}

/**
 * Get cache statistics
 */
export function getCacheStats(): { size: number; documents: string[] } {
  return {
    size: documentCache.size,
    documents: Array.from(documentCache.keys()),
  };
}
