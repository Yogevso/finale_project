import {
  createRuntimeDependencies,
  resolveCollabServerConfigFromEnv,
} from '../server/collabServerApp.js';
import { verifyCollabToken as verifyCollabTokenFn } from '../auth.js';
import { jest } from '@jest/globals';

describe('CollabServerApp config and runtime composition', () => {
  it('resolves defaults from environment when variables are missing', () => {
    const config = resolveCollabServerConfigFromEnv({});

    expect(config.port).toBe(8002);
    expect(config.host).toBe('0.0.0.0');
    expect(config.redisUrl).toBe('');
    expect(config.debounceMs).toBe(2000);
    expect(config.maxDebounceMs).toBe(10000);
    expect(config.healthPort).toBe(8003);
  });

  it('resolves explicit environment values', () => {
    const config = resolveCollabServerConfigFromEnv({
      PORT: '9000',
      HOST: '127.0.0.1',
      REDIS_URL: 'redis://localhost:6379',
      DEBOUNCE_MS: '1500',
      MAX_DEBOUNCE_MS: '7000',
    });

    expect(config.port).toBe(9000);
    expect(config.host).toBe('127.0.0.1');
    expect(config.redisUrl).toBe('redis://localhost:6379');
    expect(config.debounceMs).toBe(1500);
    expect(config.maxDebounceMs).toBe(7000);
    expect(config.healthPort).toBe(9001);
  });

  it('allows runtime dependency overrides', () => {
    const customVerify = jest.fn();
    const runtime = createRuntimeDependencies({
      verifyCollabToken: customVerify as unknown as typeof verifyCollabTokenFn,
    });

    expect(runtime.verifyCollabToken).toBe(customVerify);
  });
});
