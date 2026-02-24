/**
 * Hocuspocus Collaboration Server
 * 
 * Real-time document collaboration using Yjs CRDT
 * Handles WebSocket connections, authentication, and persistence
 */

import 'dotenv/config';
import { randomUUID } from 'crypto';
import http from 'http';
import { Server, Extension } from '@hocuspocus/server';
import { Logger } from '@hocuspocus/extension-logger';
import { Database } from '@hocuspocus/extension-database';
import { Redis } from '@hocuspocus/extension-redis';
import * as Y from 'yjs';

import { verifyCollabToken, extractToken, extractDocumentId, canWrite } from './auth.js';
import { loadDocument, saveDocument, yjsToHtml, clearDocumentCache } from './persistence.js';
import type { ConnectionContext, AwarenessUser } from './types.js';
import { getUserColor } from './types.js';
import {
  clearDocumentAuth,
  getDocumentTokenForLoad,
  getDocumentTokenForStore,
  registerDocumentConnectionAuth,
  unregisterDocumentConnectionAuth,
} from './documentAuthStore.js';

const PORT = parseInt(process.env.PORT || '8002', 10);
const HOST = process.env.HOST || '0.0.0.0';
const REDIS_URL = process.env.REDIS_URL || '';

// Track active connections by unique connection ID per document.
const activeConnections = new Map<string, Map<string, ConnectionContext>>();

/**
 * Build extensions array (conditionally includes Redis)
 */
function buildExtensions(): Extension[] {
  const extensions: Extension[] = [
    // Logging extension
    new Logger({
      log: (message) => {
        console.log(`[Hocuspocus] ${message}`);
      },
      onLoadDocument: true,
      onStoreDocument: true,
      onConnect: true,
      onDisconnect: true,
      onChange: false, // Too noisy
    }),
  ];

  // Add Redis extension for horizontal scaling if configured
  if (REDIS_URL) {
    console.log(`[Config] Redis enabled: ${REDIS_URL}`);
    extensions.push(
      new Redis({
        host: new URL(REDIS_URL).hostname,
        port: parseInt(new URL(REDIS_URL).port || '6379', 10),
      })
    );
  } else {
    console.log('[Config] Redis not configured - running in single-server mode');
  }

  return extensions;
}

/**
 * Main Hocuspocus Server Configuration
 */
const server = Server.configure({
  name: 'collab-server',
  port: PORT,
  address: HOST,
  
  // Debounce saves to reduce backend calls
  debounce: parseInt(process.env.DEBOUNCE_MS || '2000', 10),
  maxDebounce: parseInt(process.env.MAX_DEBOUNCE_MS || '10000', 10),
  
  // Quiet mode - we use Logger extension instead
  quiet: true,

  extensions: [
    ...buildExtensions(),

    // Database persistence extension
    new Database({
      fetch: async ({ documentName }) => {
        const documentId = extractDocumentId(documentName);
        const token = getDocumentTokenForLoad(documentId);
        
        if (!token) {
          console.log(`[Database] No token available for document ${documentId}`);
          return null;
        }

        const state = await loadDocument(documentId, token);
        return state;
      },

      store: async ({ documentName, state }) => {
        const documentId = extractDocumentId(documentName);
        const token = getDocumentTokenForStore(documentId);
        
        if (!token) {
          console.error(`[Database] No write-capable token available to save document ${documentId}`);
          return;
        }

        await saveDocument(documentId, state, token);
      },
    }),
  ],

  /**
   * Authentication hook - runs on every WebSocket connection
   */
  async onAuthenticate({ documentName, token: rawToken, requestParameters, connection }) {
    const documentId = extractDocumentId(documentName);
    const token = rawToken || extractToken(requestParameters);

    if (!token) {
      throw new Error('No authentication token provided');
    }

    // Verify the JWT token
    const authResult = verifyCollabToken(token, documentId);

    if (!authResult.success || !authResult.user) {
      throw new Error(authResult.error || 'Authentication failed');
    }

    const writeCapable = canWrite(authResult.permissions || []);

    // Store user context for this connection
    const connectionContext: ConnectionContext = {
      ...authResult.user,
      documentId,
      connectionId: randomUUID(),
      canWrite: writeCapable,
      connectedAt: new Date(),
    };

    // Set read-only mode if user doesn't have write permission
    if (!writeCapable) {
      connection.readOnly = true;
    }

    console.log(`[Auth] User ${authResult.user.username} authenticated for document ${documentId} (readonly: ${connection.readOnly})`);

    // Track connection by unique connection ID (supports multi-tab/user sessions).
    if (!activeConnections.has(documentId)) {
      activeConnections.set(documentId, new Map());
    }
    activeConnections.get(documentId)!.set(connectionContext.connectionId, connectionContext);
    registerDocumentConnectionAuth({
      documentId,
      connectionId: connectionContext.connectionId,
      token,
      writeCapable,
    });

    // Return user data for awareness
    return {
      user: authResult.user,
      permissions: authResult.permissions,
      connectionId: connectionContext.connectionId,
    };
  },

  /**
   * Called when a document is loaded
   */
  async onLoadDocument({ document, documentName, context }) {
    const documentId = extractDocumentId(documentName);
    console.log(`[Document] Loading document ${documentId}`);

    // If document is empty, we could initialize with content from backend
    // For now, we let the frontend handle initial content
  },

  /**
   * Called when document changes
   */
  async onChange({ documentName, document, context }) {
    const documentId = extractDocumentId(documentName);
    
    // Generate HTML preview for potential indexing
    // const html = yjsToHtml(document);
    // Could send to backend for search indexing here
  },

  /**
   * Called when awareness (presence) updates
   */
  async onAwarenessUpdate({ documentName, awareness, states }) {
    const documentId = extractDocumentId(documentName);
    const users: AwarenessUser[] = [];

    states.forEach((state, clientId) => {
      if (state.user) {
        users.push({
          userId: state.user.userId,
          username: state.user.username,
          color: state.user.color || getUserColor(state.user.userId),
          cursor: state.cursor,
        });
      }
    });

    // Could broadcast presence updates to a pub/sub system here
    // console.log(`[Awareness] Document ${documentId} has ${users.length} active users`);
  },

  /**
   * Called when a client disconnects
   */
  async onDisconnect({ documentName, context }) {
    const documentId = extractDocumentId(documentName);
    const user = context?.user;
    const connectionId = context?.connectionId as string | undefined;

    const docConnections = activeConnections.get(documentId);
    if (docConnections) {
      if (connectionId) {
        docConnections.delete(connectionId);
        unregisterDocumentConnectionAuth(documentId, connectionId);
      } else if (user?.userId) {
        // Backward-compatible fallback for contexts created without connectionId.
        for (const [id, tracked] of docConnections.entries()) {
          if (tracked.userId === user.userId) {
            docConnections.delete(id);
            unregisterDocumentConnectionAuth(documentId, id);
            break;
          }
        }
      }

      if (docConnections.size === 0) {
        activeConnections.delete(documentId);
        clearDocumentAuth(documentId);
        clearDocumentCache(documentId);
      }
    }

    if (user) {
      console.log(`[Disconnect] User ${user.username} left document ${documentId}`);
    }
  },

  /**
   * Called when the document is closed (no more connections)
   */
  async onStoreDocument({ documentName, document }) {
    const documentId = extractDocumentId(documentName);
    const state = Y.encodeStateAsUpdate(document);
    console.log(`[Store] Final save for document ${documentId} (${state.length} bytes)`);
  },
});

/**
 * Health check endpoint info
 */
function getServerInfo() {
  const documents: { [key: string]: number } = {};
  activeConnections.forEach((connections, docId) => {
    documents[docId] = connections.size;
  });

  return {
    name: 'collab-server',
    status: 'healthy',
    port: PORT,
    activeDocuments: activeConnections.size,
    documents,
    uptime: process.uptime(),
  };
}

/**
 * Simple HTTP server for health checks
 */
const healthServer = http.createServer((req, res) => {
  if (req.url === '/health' || req.url === '/') {
    const info = getServerInfo();
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(info));
  } else if (req.url === '/ready') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ready' }));
  } else {
    res.writeHead(404);
    res.end('Not found');
  }
});

// Start the server
console.log('╔════════════════════════════════════════════╗');
console.log('║  Hocuspocus Collaboration Server           ║');
console.log('╠════════════════════════════════════════════╣');
console.log(`║  WebSocket Port: ${PORT}                        ║`);
console.log(`║  Health Port: ${PORT + 1}                           ║`);
console.log(`║  Host: ${HOST}                             ║`);
if (REDIS_URL) {
  console.log('║  Redis: ENABLED                            ║');
} else {
  console.log('║  Redis: DISABLED (single-server mode)      ║');
}
console.log('╚════════════════════════════════════════════╝');

// Start health check HTTP server on health port (PORT + 1)
const HEALTH_PORT = PORT + 1;

healthServer.listen(HEALTH_PORT, HOST, () => {
  console.log(`[Health] HTTP health check available at http://${HOST}:${HEALTH_PORT}/health`);
});

// Start Hocuspocus WebSocket server
server.listen().then(() => {
  console.log(`[Server] Hocuspocus server running on ws://${HOST}:${PORT}`);
  console.log(`[Server] Connect to: ws://${HOST}:${PORT}/document/{documentId}?token={jwt}`);
});

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('\n[Server] Shutting down...');
  await server.destroy();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('\n[Server] Shutting down...');
  await server.destroy();
  process.exit(0);
});

// Export for testing
export { server, getServerInfo };
