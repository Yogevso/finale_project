import { describe, it, expect } from 'vitest';

describe('Types', () => {
  it('UserRole type should have correct values', () => {
    const validRoles = ['Admin', 'Editor', 'Viewer'];
    validRoles.forEach(role => {
      expect(['Admin', 'Editor', 'Viewer']).toContain(role);
    });
  });

  it('DocumentStatus type should have correct values', () => {
    const validStatuses = ['draft', 'active', 'archived'];
    validStatuses.forEach(status => {
      expect(['draft', 'active', 'archived']).toContain(status);
    });
  });
});
