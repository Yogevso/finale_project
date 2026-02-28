/**
 * Hocuspocus collaboration server bootstrap entrypoint.
 */

import 'dotenv/config';

import { CollabServerApp } from './server/index.js';

const app = new CollabServerApp();

async function bootstrap(): Promise<void> {
  app.printStartupBanner();
  await app.start();
}

async function shutdown(signal: NodeJS.Signals): Promise<void> {
  console.log(`[Server] Received ${signal}, shutting down...`);
  try {
    await app.stop();
    process.exit(0);
  } catch (error) {
    console.error('[Server] Shutdown failed:', error);
    process.exit(1);
  }
}

void bootstrap().catch((error) => {
  console.error('[Server] Startup failed:', error);
  process.exit(1);
});

process.on('SIGINT', () => {
  void shutdown('SIGINT');
});

process.on('SIGTERM', () => {
  void shutdown('SIGTERM');
});
