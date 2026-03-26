export interface DocumentStateTransportPort {
  loadDocumentState(
    documentId: string,
    token: string,
    traceId?: string,
  ): Promise<Uint8Array | null>;
  saveDocumentState(
    documentId: string,
    state: Uint8Array,
    token: string,
    traceId?: string,
  ): Promise<void>;
}
