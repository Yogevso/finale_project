import { getUserColor, type UserContext } from '../types.js';
import {
  COLLAB_TOKEN_TYPE,
  isCollaborationTokenContract,
  type CollaborationPermission,
} from '../authContext/contracts.js';

export interface TokenContractMappingResult {
  success: boolean;
  user?: UserContext;
  permissions?: CollaborationPermission[];
  error?: string;
}

export class CollaborationTokenContractAdapter {
  mapDecodedToken(decoded: unknown, documentId: string): TokenContractMappingResult {
    if (!isCollaborationTokenContract(decoded)) {
      return {
        success: false,
        error: 'Invalid token',
      };
    }

    if (decoded.type && decoded.type !== COLLAB_TOKEN_TYPE) {
      return {
        success: false,
        error: 'Invalid token',
      };
    }

    if (decoded.document_id !== documentId) {
      return {
        success: false,
        error: 'Token is not valid for this document',
      };
    }

    return {
      success: true,
      user: {
        userId: decoded.sub,
        username: decoded.username,
        email: decoded.email,
        role: decoded.role,
        color: getUserColor(decoded.sub),
      },
      permissions: decoded.permissions,
    };
  }
}
