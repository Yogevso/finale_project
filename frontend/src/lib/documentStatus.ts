/**
 * One label, one tone and one explanation per document status.
 *
 * There were two independent formatters. The internal table was a chain of ternaries
 * that named only `active` and `approved` and let everything else fall through to the
 * raw enum, so `draft` appeared lowercase beside `Published` in the same table and
 * `pending_review` would have shown its underscore. The public pages ran a generic
 * title-caser, which reads `active` as "Active" - correct English for the enum, and a
 * different word from the one the internal screens use for the same state.
 *
 * `PUBLISHED` and `ACTIVE` are the same value in the backend enum, so "Published" is
 * the one name for it here. `approved` is a real state between review and publication -
 * a reviewer has accepted the document and it is not yet visible to customers - which
 * is what the description says, because a five-letter pill cannot.
 */

interface StatusPresentation {
  label: string
  tone: string
  description: string
}

const STATUS_PRESENTATION: Record<string, StatusPresentation> = {
  draft: {
    label: 'Draft',
    tone: 'bg-slate-100 text-slate-700 border-slate-200',
    description: 'Being written. Not visible outside the internal portal.',
  },
  pending_review: {
    label: 'In Review',
    tone: 'bg-purple-50 text-purple-700 border-purple-200',
    description: 'Submitted for review and waiting on a reviewer.',
  },
  approved: {
    label: 'Approved',
    tone: 'bg-blue-50 text-blue-700 border-blue-200',
    description: 'A reviewer accepted it. Not yet visible to customers.',
  },
  active: {
    label: 'Published',
    tone: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    description: 'Live, and visible to everyone its visibility allows.',
  },
  archived: {
    label: 'Archived',
    tone: 'bg-slate-100 text-slate-600 border-slate-200',
    description: 'Withdrawn from circulation and kept for the record.',
  },
}

/** Title-case an unknown status rather than leaking `pending_review` into the page. */
function humanize(status: string): string {
  return status
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

export function documentStatusLabel(status: string | null | undefined): string {
  if (!status) {
    return ''
  }
  return STATUS_PRESENTATION[status]?.label ?? humanize(status)
}

export function documentStatusTone(status: string | null | undefined): string {
  return STATUS_PRESENTATION[status ?? '']?.tone ?? 'bg-slate-100 text-slate-600 border-slate-200'
}

export function documentStatusDescription(status: string | null | undefined): string {
  return STATUS_PRESENTATION[status ?? '']?.description ?? ''
}
