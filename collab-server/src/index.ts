/**
 * Hocuspocus collaboration server bootstrap entrypoint.
 */

import 'dotenv/config';

import { createStructuredLogger } from './logger.js';
import { CollabServerApp } from './server/index.js';

const app = new CollabServerApp();
const logger = createStructuredLogger('collab.bootstrap');

async function bootstrap(): Promise<void> {
  app.printStartupBanner();
  await app.start();
}

async function shutdown(signal: NodeJS.Signals): Promise<void> {
  logger.info('Received shutdown signal', { signal });
  try {
    await app.stop();
    process.exit(0);
  } catch (error) {
    logger.error('Shutdown failed', { signal, error });
    process.exit(1);
  }
}

void bootstrap().catch((error) => {
  logger.error('Startup failed', { error });
  process.exit(1);
});

process.on('SIGINT', () => {
  void shutdown('SIGINT');
});

process.on('SIGTERM', () => {
  void shutdown('SIGTERM');
});
