export class DocumentStateContractAdapter {
  normalizeLoadedState(state: unknown): Uint8Array | null {
    if (!(state instanceof Uint8Array) || state.length === 0) {
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
