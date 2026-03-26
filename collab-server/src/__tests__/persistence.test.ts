import {
  decodeCacheInvalidationMessage,
  encodeCacheInvalidationMessage,
  resolveCacheInvalidationSecret,
} from '../persistence.js';

describe('cache invalidation message signing', () => {
  it('prefers CACHE_INVALIDATION_SECRET over JWT_SECRET', () => {
    expect(
      resolveCacheInvalidationSecret({
        CACHE_INVALIDATION_SECRET: 'cache-secret',
        SECRET_KEY: 'shared-secret',
        JWT_SECRET: 'jwt-secret',
      }),
    ).toBe('cache-secret');
  });

  it('falls back to SECRET_KEY when no dedicated cache secret is set', () => {
    expect(
      resolveCacheInvalidationSecret({
        SECRET_KEY: 'shared-secret',
      }),
    ).toBe('shared-secret');
  });

  it('falls back to JWT_SECRET for legacy environments', () => {
    expect(
      resolveCacheInvalidationSecret({
        JWT_SECRET: 'jwt-secret',
      }),
    ).toBe('jwt-secret');
  });

  it('round-trips a signed invalidation payload', () => {
    const issuedAt = 1_700_000_000_000;
    const payload = encodeCacheInvalidationMessage('123', 'cache-secret', issuedAt);

    expect(
      decodeCacheInvalidationMessage(payload, 'cache-secret', issuedAt + 1000),
    ).toBe('123');
  });

  it('rejects invalid signatures', () => {
    const issuedAt = 1_700_000_000_000;
    const payload = encodeCacheInvalidationMessage('123', 'cache-secret', issuedAt);
    const tampered = payload.replace('123', '124');

    expect(
      decodeCacheInvalidationMessage(tampered, 'cache-secret', issuedAt + 1000),
    ).toBeNull();
  });

  it('rejects stale payloads', () => {
    const issuedAt = 1_700_000_000_000;
    const payload = encodeCacheInvalidationMessage('123', 'cache-secret', issuedAt);

    expect(
      decodeCacheInvalidationMessage(payload, 'cache-secret', issuedAt + 301_000),
    ).toBeNull();
  });
});
