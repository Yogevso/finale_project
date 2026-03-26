import jwt from 'jsonwebtoken';

import { CollaborationTokenContractAdapter } from '../adapters/collaborationTokenContractAdapter.js';
import type { UserContext } from '../types.js';
import type { CollaborationPermission } from './contracts.js';

export interface AuthResult {
  success: boolean;
  user?: UserContext;
  permissions?: CollaborationPermission[];
  error?: string;
}

export function resolveCollaborationJwtSecret(env: NodeJS.ProcessEnv = process.env): string {
  const secret = env.SECRET_KEY || env.JWT_SECRET;

  if (!secret) {
    console.error('FATAL: SECRET_KEY environment variable is required (JWT_SECRET is a legacy fallback)');
    process.exit(1);
  }

  if (secret.length < 32) {
    const nodeEnv = env.NODE_ENV || 'development';
    if (nodeEnv === 'production') {
      console.error('FATAL: collaboration signing secret is too short. Use at least 32 characters.');
      process.exit(1);
    }
    if (secret.length < 16) {
      console.error('FATAL: collaboration signing secret must be at least 16 characters, even in development.');
      process.exit(1);
    }
    console.warn('WARNING: collaboration signing secret is shorter than recommended (32+ chars)');
  }

  return secret;
}

export class CollaborationAuthService {
  private readonly jwtSecret: string;
  private readonly contractAdapter: CollaborationTokenContractAdapter;

  constructor(
    jwtSecret: string = resolveCollaborationJwtSecret(),
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
