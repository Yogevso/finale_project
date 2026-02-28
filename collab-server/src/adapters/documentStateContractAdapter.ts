export class DocumentStateContractAdapter {
  normalizeLoadedState(state: Uint8Array | null): Uint8Array | null {
    if (!state || state.length === 0) {
      return null;
    }
    return state;
  }

  toErrorMessage(error: unknown): string {
    if (error instanceof Error && error.message.trim()) {
      return error.message;
    }
    return 'Unknown error';
  }
}
