import type { ReviewSectionStatus } from './reviewDiff';

export type ReviewDocumentHighlightStatus = ReviewSectionStatus | 'suggested';

export interface ReviewDocumentSessionEntry {
  id: string;
  title: string;
  status: ReviewDocumentHighlightStatus;
  anchorId?: string;
}

export interface ReviewDocumentSession {
  reviewId: number;
  documentId: number;
  mode: 'review' | 'suggestions';
  focusedEntryId?: string;
  entries: ReviewDocumentSessionEntry[];
  updatedAt: string;
}

const STORAGE_KEY = 'reviews.document.session.v1';

function canUseStorage(): boolean {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

function readStore(): Record<string, ReviewDocumentSession> {
  if (!canUseStorage()) {
    return {};
  }

  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return {};
  }

  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function writeStore(store: Record<string, ReviewDocumentSession>) {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

export function persistReviewDocumentSession(
  session: ReviewDocumentSession
): ReviewDocumentSession {
  const store = readStore();
  const nextSession = {
    ...session,
    updatedAt: new Date().toISOString(),
  };

  store[String(session.reviewId)] = nextSession;
  writeStore(store);
  return nextSession;
}

export function getReviewDocumentSession(reviewId: number): ReviewDocumentSession | null {
  return readStore()[String(reviewId)] || null;
}
