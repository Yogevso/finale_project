import { DocumentStateContractAdapter } from '../adapters/documentStateContractAdapter.js';

describe('DocumentStateContractAdapter', () => {
  const adapter = new DocumentStateContractAdapter();

  it('normalizes missing state payloads to null', () => {
    expect(adapter.normalizeLoadedState(null)).toBeNull();
    expect(adapter.normalizeLoadedState(new Uint8Array())).toBeNull();
  });

  it('preserves non-empty state payloads', () => {
    const payload = new Uint8Array([1, 2, 3]);

    expect(adapter.normalizeLoadedState(payload)).toEqual(payload);
  });

  it('extracts readable error messages', () => {
    expect(adapter.toErrorMessage(new Error('network error'))).toBe('network error');
    expect(adapter.toErrorMessage('bad')).toBe('Unknown error');
  });
});
