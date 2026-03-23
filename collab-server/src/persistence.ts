/**
 * Document Persistence for Hocuspocus
 * Saves Yjs state to FastAPI backend
 */

import * as Y from 'yjs';
import { Redis } from 'ioredis';
import { DocumentStateContractAdapter } from './adapters/documentStateContractAdapter.js';
import {
  BackendDocumentStateTransportAdapter,
  buildDocumentStateUrl,
} from './adapters/backendDocumentStateTransportAdapter.js';
import type { DocumentStateTransportPort } from './ports/documentStateTransportPort.js';

export { buildDocumentStateUrl };

// In-memory cache for document states (for quick access)
const documentCache = new Map<string, Uint8Array>();
const MAX_CACHE_SIZE = 200;

// Cache invalidation via Redis pub/sub for horizontal scaling.
// When a document is saved on one instance, all other instances evict
// their local cache entry so the next load fetches fresh state.
const CACHE_INVALIDATION_CHANNEL = 'collab:cache:invalidate';
let redisPub: Redis | null = null;
let redisSub: Redis | null = null;

export async function initCacheInvalidation(redisUrl: string): Promise<void> {
  if (!redisUrl) return;

  redisPub = new Redis(redisUrl);
  redisSub = new Redis(redisUrl);

  await redisSub.subscribe(CACHE_INVALIDATION_CHANNEL);

  redisSub.on('message', (_channel: string, message: string) => {
    const documentId = message;
    if (documentCache.has(documentId)) {
      documentCache.delete(documentId);
      console.log(`[CacheInval] Evicted cache for document ${documentId} (remote save)`);
    }
  });

  console.log('[CacheInval] Redis cache invalidation active');
}

export async function stopCacheInvalidation(): Promise<void> {
  if (redisSub) {
    await redisSub.unsubscribe(CACHE_INVALIDATION_CHANNEL);
    redisSub.disconnect();
    redisSub = null;
  }
  if (redisPub) {
    redisPub.disconnect();
    redisPub = null;
  }
}

function publishCacheInvalidation(documentId: string): void {
  if (redisPub) {
    redisPub.publish(CACHE_INVALIDATION_CHANNEL, documentId).catch((err: unknown) => {
      console.error(`[CacheInval] Failed to publish invalidation for ${documentId}:`, err);
    });
  }
}

function cacheSet(documentId: string, state: Uint8Array): void {
  // Delete first so re-insertion moves key to end (most recent)
  documentCache.delete(documentId);
  documentCache.set(documentId, state);
  // Evict oldest entries when cache exceeds limit
  while (documentCache.size > MAX_CACHE_SIZE) {
    const oldest = documentCache.keys().next().value;
    if (oldest !== undefined) {
      documentCache.delete(oldest);
    } else {
      break;
    }
  }
}

export interface PersistenceResult {
  success: boolean;
  error?: string;
}

const defaultTransport: DocumentStateTransportPort = new BackendDocumentStateTransportAdapter();
const stateContractAdapter = new DocumentStateContractAdapter();

/**
 * Load document state from FastAPI backend
 */
export async function loadDocument(
  documentId: string,
  token: string,
  transport: DocumentStateTransportPort = defaultTransport,
): Promise<Uint8Array | null> {
  // Check cache first
  const cached = documentCache.get(documentId);
  if (cached) {
    console.log(`[Persistence] Loaded document ${documentId} from cache`);
    return cached;
  }

  try {
    const state = stateContractAdapter.normalizeLoadedState(
      await transport.loadDocumentState(documentId, token),
    );
    if (state) {
      cacheSet(documentId, state);
      console.log(`[Persistence] Loaded document ${documentId} from backend (${state.length} bytes)`);
      return state;
    }
    console.log(`[Persistence] Document ${documentId} has no existing state`);
    return null;
  } catch (error) {
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
  token: string,
  transport: DocumentStateTransportPort = defaultTransport,
): Promise<PersistenceResult> {
  // Update cache
  cacheSet(documentId, state);

  try {
    await transport.saveDocumentState(documentId, state, token);
    publishCacheInvalidation(documentId);

    console.log(`[Persistence] Saved document ${documentId} to backend (${state.length} bytes)`);
    return { success: true };
  } catch (error) {
    console.error(`[Persistence] Failed to save document ${documentId}:`, error);
    return {
      success: false,
      error: stateContractAdapter.toErrorMessage(error),
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
