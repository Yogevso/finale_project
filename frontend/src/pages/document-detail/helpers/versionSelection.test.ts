import { describe, expect, it } from 'vitest'
import type { Version } from '@/types'
import {
  getAuthoritativeVersionCandidates,
  selectAuthoritativeVersion,
} from '@/pages/document-detail/helpers/versionSelection'

function buildVersion(overrides: Partial<Version> = {}): Version {
  return {
    id: 1,
    document_id: 42,
    version_number: 1,
    semantic_version: '1.0.0',
    content: '<h1>Version</h1>',
    changes_summary: null,
    is_published: false,
    published_at: null,
    created_by: 7,
    created_at: '2026-01-01T00:00:00Z',
    latest_review: null,
    ...overrides,
  }
}

describe('versionSelection', () => {
  it('prefers the explicitly requested review-session version first', () => {
    const approved = buildVersion({
      id: 10,
      semantic_version: '1.0.0',
      latest_review: {
        id: 100,
        status: 'approved',
        submitted_at: '2026-01-10T00:00:00Z',
        reviewed_at: '2026-01-11T00:00:00Z',
        submitted_by: 7,
      },
    })
    const rejected = buildVersion({
      id: 11,
      semantic_version: '1.1.0',
      latest_review: {
        id: 101,
        status: 'rejected',
        submitted_at: '2026-01-12T00:00:00Z',
        reviewed_at: '2026-01-13T00:00:00Z',
        submitted_by: 7,
      },
    })

    const ordered = getAuthoritativeVersionCandidates({
      versions: [approved, rejected],
      preferredVersionId: approved.id,
    })

    expect(ordered[0]?.id).toBe(approved.id)
  })

  it('defaults to active draft work before an older approved version', () => {
    const approved = buildVersion({
      id: 20,
      semantic_version: '2.0.0',
      created_at: '2026-02-10T00:00:00Z',
      latest_review: {
        id: 200,
        status: 'approved',
        submitted_at: '2026-02-10T00:00:00Z',
        reviewed_at: '2026-02-11T00:00:00Z',
        submitted_by: 7,
      },
    })
    const newerDraft = buildVersion({
      id: 21,
      semantic_version: '2.1.0',
      created_at: '2026-02-12T00:00:00Z',
      latest_review: null,
    })

    const selected = selectAuthoritativeVersion({
      versions: [newerDraft, approved],
    })

    expect(selected?.id).toBe(newerDraft.id)
  })

  it('defaults to the most recently approved version before a published fallback', () => {
    const approved = buildVersion({
      id: 30,
      semantic_version: '3.0.0',
      is_published: false,
      latest_review: {
        id: 300,
        status: 'approved',
        submitted_at: '2026-03-10T00:00:00Z',
        reviewed_at: '2026-03-11T00:00:00Z',
        submitted_by: 7,
      },
    })
    const published = buildVersion({
      id: 31,
      semantic_version: '3.1.0',
      is_published: true,
      published_at: '2026-03-12T00:00:00Z',
      latest_review: null,
    })

    const selected = selectAuthoritativeVersion({
      versions: [published, approved],
    })

    expect(selected?.id).toBe(approved.id)
  })
})
