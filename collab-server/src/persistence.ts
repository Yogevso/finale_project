/**
 * Document Persistence for Hocuspocus
 * Saves Yjs state to FastAPI backend
 */

import { createHmac, timingSafeEqual } from 'crypto';

import * as Y from 'yjs';
import { Redis } from 'ioredis';
import jwt from 'jsonwebtoken';
import { DocumentStateContractAdapter } from './adapters/documentStateContractAdapter.js';
import {
  BackendDocumentStateTransportAdapter,
  buildDocumentStateUrl,
} from './adapters/backendDocumentStateTransportAdapter.js';
import { createStructuredLogger } from './logger.js';
import type { DocumentStateTransportPort } from './ports/documentStateTransportPort.js';
import { extractTraceIdFromToken } from './trace.js';

export { buildDocumentStateUrl };

// In-memory cache for document states (for quick access)
const documentCache = new Map<string, Uint8Array>();
const MAX_CACHE_SIZE = 200;

// Cache invalidation via Redis pub/sub for horizontal scaling.
// When a document is saved on one instance, all other instances evict
// their local cache entry so the next load fetches fresh state.
const CACHE_INVALIDATION_CHANNEL = 'collab:cache:invalidate';
const CACHE_INVALIDATION_MAX_AGE_MS = 5 * 60 * 1000;
let redisPub: Redis | null = null;
let redisSub: Redis | null = null;
let cacheInvalidationSecret = '';
const persistenceLogger = createStructuredLogger('collab.persistence');
const cacheLogger = createStructuredLogger('collab.cache_invalidation');

type CacheInvalidationEnvelope = {
  documentId: string;
  issuedAt: number;
  signature: string;
};

export function resolveCacheInvalidationSecret(
  env: NodeJS.ProcessEnv = process.env,
): string {
  return env.CACHE_INVALIDATION_SECRET || env.SECRET_KEY || env.JWT_SECRET || '';
}

export function signCacheInvalidationMessage(
  documentId: string,
  issuedAt: number,
  secret: string,
): string {
  return createHmac('sha256', secret).update(`${documentId}:${issuedAt}`).digest('hex');
}

export function encodeCacheInvalidationMessage(
  documentId: string,
  secret: string,
  issuedAt: number = Date.now(),
): string {
  return JSON.stringify({
    documentId,
    issuedAt,
    signature: signCacheInvalidationMessage(documentId, issuedAt, secret),
  } satisfies CacheInvalidationEnvelope);
}

export function decodeCacheInvalidationMessage(
  payload: string,
  secret: string,
  now: number = Date.now(),
): string | null {
  try {
    const parsed = JSON.parse(payload) as Partial<CacheInvalidationEnvelope>;
    if (
      typeof parsed.documentId !== 'string'
      || !parsed.documentId
      || typeof parsed.issuedAt !== 'number'
      || typeof parsed.signature !== 'string'
    ) {
      return null;
    }

    if (Math.abs(now - parsed.issuedAt) > CACHE_INVALIDATION_MAX_AGE_MS) {
      return null;
    }

    const expected = signCacheInvalidationMessage(parsed.documentId, parsed.issuedAt, secret);
    const actualBuffer = Buffer.from(parsed.signature, 'hex');
    const expectedBuffer = Buffer.from(expected, 'hex');
    if (
      actualBuffer.length !== expectedBuffer.length
      || !timingSafeEqual(actualBuffer, expectedBuffer)
    ) {
      return null;
    }

    return parsed.documentId;
  } catch {
    return null;
  }
}

export async function initCacheInvalidation(redisUrl: string, secret: string): Promise<void> {
  if (!redisUrl) return;
  if (!secret) {
    throw new Error('Cache invalidation secret is required when Redis invalidation is enabled');
  }

  cacheInvalidationSecret = secret;

  redisPub = new Redis(redisUrl);
  redisSub = new Redis(redisUrl);

  await redisSub.subscribe(CACHE_INVALIDATION_CHANNEL);

  redisSub.on('message', (_channel: string, message: string) => {
    const documentId = decodeCacheInvalidationMessage(message, cacheInvalidationSecret);
    if (!documentId) {
      cacheLogger.warn('Ignored invalid invalidation payload');
      return;
    }

    if (documentCache.has(documentId)) {
      documentCache.delete(documentId);
      cacheLogger.info('Evicted cached document after remote save', { documentId });
    }
  });

  cacheLogger.info('Redis cache invalidation active');
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
  if (redisPub && cacheInvalidationSecret) {
    redisPub.publish(
      CACHE_INVALIDATION_CHANNEL,
      encodeCacheInvalidationMessage(documentId, cacheInvalidationSecret),
    ).catch((err: unknown) => {
      cacheLogger.error('Failed to publish invalidation', {
        documentId,
        error: err,
      });
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
  // H-21: Verify the token is actually meant for this document
  const decoded = jwt.decode(token) as Record<string, unknown> | null;
  if (!decoded || String(decoded.document_id) !== String(documentId)) {
    persistenceLogger.warn('Token document_id mismatch during load', { documentId });
    return null;
  }
  const traceId = extractTraceIdFromToken(token);

  // Check cache first
  const cached = documentCache.get(documentId);
  if (cached) {
    persistenceLogger.info('Loaded document from cache', { documentId, traceId });
    return cached;
  }

  try {
    const state = stateContractAdapter.normalizeLoadedState(
      await transport.loadDocumentState(documentId, token, traceId),
    );
    if (state) {
      cacheSet(documentId, state);
      persistenceLogger.info('Loaded document from backend', {
        documentId,
        traceId,
        bytes: state.length,
      });
      return state;
    }
    persistenceLogger.info('Document has no existing persisted state', { documentId, traceId });
    return null;
  } catch (error) {
    persistenceLogger.error('Failed to load document', { documentId, traceId, error });
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
  // H-21: Verify the token is actually meant for this document
  const decoded = jwt.decode(token) as Record<string, unknown> | null;
  if (!decoded || String(decoded.document_id) !== String(documentId)) {
    persistenceLogger.warn('Token document_id mismatch during save', { documentId });
    return { success: false, error: 'Token is not valid for this document' };
  }
  const traceId = extractTraceIdFromToken(token);

  // Update cache
  cacheSet(documentId, state);

  try {
    await transport.saveDocumentState(documentId, state, token, traceId);
    publishCacheInvalidation(documentId);

    persistenceLogger.info('Saved document to backend', {
      documentId,
      traceId,
      bytes: state.length,
    });
    return { success: true };
  } catch (error) {
    persistenceLogger.error('Failed to save document', {
      documentId,
      traceId,
      bytes: state.length,
      error,
    });
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
  persistenceLogger.info('Cleared cached document state', { documentId });
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
