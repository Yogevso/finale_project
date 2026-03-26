import fs from 'node:fs';
import { CollaborationTokenContractAdapter } from '../../adapters/collaborationTokenContractAdapter.js';
import {
  COLLAB_TOKEN_TYPE,
  isCollaborationTokenContract,
} from '../../authContext/contracts.js';

const contract = JSON.parse(
  fs.readFileSync(new URL('./backendProvider.contract.json', import.meta.url), 'utf8'),
) as {
  contract_version: string;
  consumer: string;
  provider: string;
  collaboration_token: {
    token_type: string;
    allowed_permissions: string[];
    required_claims: string[];
      fixture: {
        sub: string;
        username: string;
        email: string;
        role: string;
        tenant_id: number;
        document_id: string;
        permissions: string[];
        type: string;
      };
  };
};

describe('collab-server consumer contract', () => {
  const tokenContract = contract.collaboration_token;
  const adapter = new CollaborationTokenContractAdapter();

  it('uses a semver contract version marker', () => {
    expect(contract.contract_version).toMatch(/^\d+\.\d+\.\d+$/);
    expect(contract.consumer).toBe('collab-server');
    expect(contract.provider).toBe('backend');
  });

  it('keeps token-type expectations aligned with adapter constants', () => {
    expect(tokenContract.token_type).toBe(COLLAB_TOKEN_TYPE);
  });

  it('accepts fixture payloads that satisfy required collaboration token claims', () => {
    const fixture = tokenContract.fixture;

    expect(isCollaborationTokenContract(fixture)).toBe(true);
    for (const claim of tokenContract.required_claims) {
      expect(fixture).toHaveProperty(claim);
    }

    const mapping = adapter.mapDecodedToken(fixture, fixture.document_id);
    expect(mapping.success).toBe(true);
    expect(mapping.permissions).toEqual(['read', 'write']);
    expect(mapping.user?.userId).toBe('7');
  });

  it('rejects permissions outside the contract allow-list', () => {
    const fixture = {
      ...tokenContract.fixture,
      permissions: ['read', 'admin'],
    };

    expect(isCollaborationTokenContract(fixture)).toBe(false);
    expect(tokenContract.allowed_permissions).toEqual(['read', 'write']);
  });
});
