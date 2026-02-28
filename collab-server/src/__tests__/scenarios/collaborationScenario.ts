import type { ConnectionContext } from '../../types.js';
import {
  buildConnectionContext,
  buildDocumentConnectionAuth,
} from '../factories/collaborationFixtures.js';

export interface ConnectionSetScenario {
  documentId: string;
  writeConnection: ConnectionContext;
  readConnection: ConnectionContext;
  writeAuth: ReturnType<typeof buildDocumentConnectionAuth>;
  readAuth: ReturnType<typeof buildDocumentConnectionAuth>;
}

export function buildConnectionSetScenario(
  documentId: string = 'doc-1',
): ConnectionSetScenario {
  const writeConnection = buildConnectionContext({
    documentId,
    connectionId: 'conn-1',
    userId: 'user-1',
  });
  const readConnection = buildConnectionContext({
    documentId,
    connectionId: 'conn-2',
    userId: 'user-2',
    canWrite: false,
  });

  return {
    documentId,
    writeConnection,
    readConnection,
    writeAuth: buildDocumentConnectionAuth({
      documentId,
      connectionId: writeConnection.connectionId,
      token: 'token-1',
      writeCapable: true,
    }),
    readAuth: buildDocumentConnectionAuth({
      documentId,
      connectionId: readConnection.connectionId,
      token: 'token-2',
      writeCapable: false,
    }),
  };
}
