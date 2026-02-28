import jwt from 'jsonwebtoken';

import { CollaborationTokenContractAdapter } from '../adapters/collaborationTokenContractAdapter.js';
import type { UserContext } from '../types.js';
import type { CollaborationPermission } from './contracts.js';

const DEFAULT_JWT_SECRET = 'your-secret-key-change-in-production';

export interface AuthResult {
  success: boolean;
  user?: UserContext;
  permissions?: CollaborationPermission[];
  error?: string;
}

export class CollaborationAuthService {
  private readonly jwtSecret: string;
  private readonly contractAdapter: CollaborationTokenContractAdapter;

  constructor(
    jwtSecret: string = process.env.JWT_SECRET || DEFAULT_JWT_SECRET,
    contractAdapter: CollaborationTokenContractAdapter = new CollaborationTokenContractAdapter(),
  ) {
    this.jwtSecret = jwtSecret;
    this.contractAdapter = contractAdapter;
  }

  verifyCollabToken(token: string, documentId: string): AuthResult {
    try {
      const decoded = jwt.verify(token, this.jwtSecret);
      return this.contractAdapter.mapDecodedToken(decoded, documentId);
    } catch (error) {
      if (error instanceof jwt.TokenExpiredError) {
        return {
          success: false,
          error: 'Token has expired',
        };
      }

      if (error instanceof jwt.JsonWebTokenError) {
        return {
          success: false,
          error: 'Invalid token',
        };
      }

      return {
        success: false,
        error: 'Authentication failed',
      };
    }
  }

  canWrite(permissions: CollaborationPermission[]): boolean {
    return permissions.includes('write');
  }

  canRead(permissions: CollaborationPermission[]): boolean {
    return permissions.includes('read') || permissions.includes('write');
  }
}
