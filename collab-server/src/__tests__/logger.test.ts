import { jest } from '@jest/globals';

import { createStructuredLogger } from '../logger.js';

describe('createStructuredLogger', () => {
  it('emits JSON log entries with merged scope context and normalized errors', () => {
    const sink = {
      info: jest.fn(),
      warn: jest.fn(),
      error: jest.fn(),
    };
    const logger = createStructuredLogger('collab', sink, { service: 'editor' })
      .child('persistence', { documentId: '42' });

    logger.error('Failed to save document', {
      traceId: 'trace-123',
      error: new Error('backend timeout'),
    });

    expect(sink.error).toHaveBeenCalledTimes(1);
    const payload = JSON.parse(sink.error.mock.calls[0][0] as string) as Record<string, unknown>;
    expect(payload.level).toBe('error');
    expect(payload.scope).toBe('collab.persistence');
    expect(payload.message).toBe('Failed to save document');
    expect(payload.service).toBe('editor');
    expect(payload.documentId).toBe('42');
    expect(payload.traceId).toBe('trace-123');
    expect(payload.error).toMatchObject({
      name: 'Error',
      message: 'backend timeout',
    });
  });
});
