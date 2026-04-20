export type PendingReviewWorkflowStatus = 'new' | 'in_progress';

export interface PersistedReviewProgress {
  currentSectionIndex: number;
  startedAt: string;
  updatedAt: string;
  decisionReady?: boolean;
  sectionSuggestions?: Record<string, string>;
}

const STORAGE_KEY = 'reviews.workflow.progress.v1';

function canUseStorage(): boolean {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

function readProgressStore(): Record<string, PersistedReviewProgress> {
  if (!canUseStorage()) {
    return {};
  }

  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return {};
  }

  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') {
      return {};
    }

    return Object.entries(parsed).reduce<Record<string, PersistedReviewProgress>>(
      (accumulator, [reviewId, value]) => {
        const candidate =
          value && typeof value === 'object'
            ? (value as Record<string, unknown>)
            : null;
        if (
          candidate &&
          typeof candidate.currentSectionIndex === 'number' &&
          typeof candidate.startedAt === 'string' &&
          typeof candidate.updatedAt === 'string'
        ) {
          const rawSectionSuggestions =
            candidate.sectionSuggestions &&
            typeof candidate.sectionSuggestions === 'object'
              ? (candidate.sectionSuggestions as Record<string, unknown>)
              : null;

          accumulator[reviewId] = {
            currentSectionIndex: candidate.currentSectionIndex,
            startedAt: candidate.startedAt,
            updatedAt: candidate.updatedAt,
            decisionReady: candidate.decisionReady === true,
            sectionSuggestions: rawSectionSuggestions
              ? Object.entries(rawSectionSuggestions).reduce<Record<string, string>>(
                  (suggestions, [sectionId, suggestion]) => {
                    if (typeof suggestion === 'string') {
                      suggestions[sectionId] = suggestion;
                    }
                    return suggestions;
                  },
                  {},
                )
              : {},
          };
        }
        return accumulator;
      },
      {}
    );
  } catch {
    return {};
  }
}

function writeProgressStore(store: Record<string, PersistedReviewProgress>) {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

export function getPersistedReviewProgress(reviewId: number): PersistedReviewProgress | null {
  return readProgressStore()[String(reviewId)] || null;
}

export function getPendingReviewWorkflowStatus(reviewId: number): PendingReviewWorkflowStatus {
  return getPersistedReviewProgress(reviewId) ? 'in_progress' : 'new';
}

export function markReviewStarted(
  reviewId: number,
  currentSectionIndex: number = 0
): PersistedReviewProgress {
  const now = new Date().toISOString();
  const store = readProgressStore();
  const existing = store[String(reviewId)];
  const nextProgress: PersistedReviewProgress = {
    currentSectionIndex,
    startedAt: existing?.startedAt || now,
    updatedAt: now,
    decisionReady: existing?.decisionReady === true,
    sectionSuggestions: existing?.sectionSuggestions || {},
  };

  store[String(reviewId)] = nextProgress;
  writeProgressStore(store);
  return nextProgress;
}

export function updateReviewProgress(
  reviewId: number,
  currentSectionIndex: number,
  options?: {
    decisionReady?: boolean;
    sectionSuggestions?: Record<string, string>;
  }
): PersistedReviewProgress {
  const existing = markReviewStarted(reviewId, currentSectionIndex);
  const store = readProgressStore();
  const nextProgress: PersistedReviewProgress = {
    ...existing,
    decisionReady: options?.decisionReady ?? existing.decisionReady ?? false,
    sectionSuggestions: options?.sectionSuggestions ?? existing.sectionSuggestions ?? {},
  };

  store[String(reviewId)] = nextProgress;
  writeProgressStore(store);
  return nextProgress;
}

export function setReviewDecisionReady(
  reviewId: number,
  decisionReady: boolean
): PersistedReviewProgress {
  const existing = getPersistedReviewProgress(reviewId) || markReviewStarted(reviewId, 0);
  return updateReviewProgress(reviewId, existing.currentSectionIndex, {
    decisionReady,
    sectionSuggestions: existing.sectionSuggestions || {},
  });
}

export function saveSectionSuggestion(
  reviewId: number,
  sectionId: string,
  suggestion: string
): PersistedReviewProgress {
  const existing = getPersistedReviewProgress(reviewId) || markReviewStarted(reviewId, 0);
  const nextSuggestions = { ...(existing.sectionSuggestions || {}) };
  const trimmedSuggestion = suggestion.trim();

  if (trimmedSuggestion.length === 0) {
    delete nextSuggestions[sectionId];
  } else {
    nextSuggestions[sectionId] = suggestion;
  }

  return updateReviewProgress(reviewId, existing.currentSectionIndex, {
    decisionReady: existing.decisionReady ?? false,
    sectionSuggestions: nextSuggestions,
  });
}

export function clearReviewProgress(reviewId: number) {
  const store = readProgressStore();
  if (!store[String(reviewId)]) {
    return;
  }

  delete store[String(reviewId)];
  writeProgressStore(store);
}
