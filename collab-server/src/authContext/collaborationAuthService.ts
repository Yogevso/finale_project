import jwt from 'jsonwebtoken';

import { CollaborationTokenContractAdapter } from '../adapters/collaborationTokenContractAdapter.js';
import { createStructuredLogger } from '../logger.js';
import type { UserContext } from '../types.js';
import type { CollaborationPermission } from './contracts.js';

export interface AuthResult {
  success: boolean;
  user?: UserContext;
  permissions?: CollaborationPermission[];
  error?: string;
}

const logger = createStructuredLogger('collab.auth');

export function resolveCollaborationJwtSecret(env: NodeJS.ProcessEnv = process.env): string {
  const secret = env.SECRET_KEY || env.JWT_SECRET;

  if (!secret) {
    logger.error('SECRET_KEY environment variable is required', {
      hasLegacyJwtSecret: Boolean(env.JWT_SECRET),
    });
    process.exit(1);
  }

  if (secret.length < 32) {
    const nodeEnv = env.NODE_ENV || 'development';
    if (nodeEnv === 'production') {
      logger.error('Collaboration signing secret is too short for production', {
        minRecommendedLength: 32,
        actualLength: secret.length,
      });
      process.exit(1);
    }
    if (secret.length < 16) {
      logger.error('Collaboration signing secret is too short even for development', {
        minLength: 16,
        actualLength: secret.length,
      });
      process.exit(1);
    }
    logger.warn('Collaboration signing secret is shorter than recommended', {
      recommendedLength: 32,
      actualLength: secret.length,
    });
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
