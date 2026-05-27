import type { Version } from '@/types'
import { getUsableVersionContent } from '@/pages/document-detail/helpers/previewHelpers'

function getCreatedAtTime(version: Version): number {
  return new Date(version.created_at).getTime()
}

function getPublishedAtTime(version: Version): number {
  return new Date(version.published_at || version.created_at).getTime()
}

function getReviewActivityTime(version: Version): number {
  const latestReview = version.latest_review
  return new Date(
    latestReview?.reviewed_at || latestReview?.submitted_at || version.created_at,
  ).getTime()
}

function sortByCreatedAtDesc(versions: Version[]): Version[] {
  return [...versions].sort((left, right) => getCreatedAtTime(right) - getCreatedAtTime(left))
}

function sortByPublishedAtDesc(versions: Version[]): Version[] {
  return [...versions].sort((left, right) => getPublishedAtTime(right) - getPublishedAtTime(left))
}

function sortByReviewActivityDesc(versions: Version[]): Version[] {
  return [...versions].sort(
    (left, right) => getReviewActivityTime(right) - getReviewActivityTime(left),
  )
}

export function getAuthoritativeVersionCandidates(params: {
  versions: Version[]
  preferredVersionId?: number | null
}): Version[] {
  const { versions, preferredVersionId = null } = params
  const seenVersionIds = new Set<number>()
  const orderedVersions: Version[] = []

  const pushVersions = (nextVersions: Version[]) => {
    nextVersions.forEach((version) => {
      if (seenVersionIds.has(version.id)) {
        return
      }
      seenVersionIds.add(version.id)
      orderedVersions.push(version)
    })
  }

  if (preferredVersionId) {
    pushVersions(versions.filter((version) => version.id === preferredVersionId))
  }

  pushVersions(
    sortByReviewActivityDesc(
      versions.filter((version) => version.latest_review?.status === 'pending'),
    ),
  )
  pushVersions(
    sortByCreatedAtDesc(
      versions.filter((version) => !version.is_published && !version.latest_review),
    ),
  )
  pushVersions(
    sortByReviewActivityDesc(
      versions.filter((version) => version.latest_review?.status === 'rejected'),
    ),
  )
  pushVersions(
    sortByReviewActivityDesc(
      versions.filter((version) => version.latest_review?.status === 'approved'),
    ),
  )
  pushVersions(sortByPublishedAtDesc(versions.filter((version) => version.is_published)))
  pushVersions(sortByCreatedAtDesc(versions))

  return orderedVersions
}

export function selectAuthoritativeVersion(params: {
  versions: Version[]
  preferredVersionId?: number | null
}): Version | null {
  return (
    getAuthoritativeVersionCandidates(params).find((version) =>
      Boolean(getUsableVersionContent(version.content)),
    ) || null
  )
}
