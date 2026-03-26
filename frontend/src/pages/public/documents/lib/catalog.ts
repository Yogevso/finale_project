import type {
  PublicCategoryCount,
  PublicPlatformHistoryResponse,
  PublicPlatformOverviewItem,
} from '@/lib/publicApi'

export type LatestPlatformRelease = {
  title: string
  documentNumber: string
  releaseBranch?: string
  versionLabel?: string
  versionNumber?: number
  publishedAt?: string
}

export type PlatformReleasePreview = {
  platformId?: number
  platform: string
  latestDoc: LatestPlatformRelease
}

export type CategoryTreeNode = {
  id: string
  label: string
  count: number
  selfCount: number
  filterCategory: string | null
  children: CategoryTreeNode[]
}

const CATEGORY_DELIMITER_PATTERN = /\s*(?:\/|>)\s*/

export const normalizePlatformName = (value: string) => value.trim().toLowerCase()

export const splitCategorySegments = (value: string) =>
  value
    .split(CATEGORY_DELIMITER_PATTERN)
    .map((segment) => segment.trim())
    .filter(Boolean)

export function buildCategoryTree(items: PublicCategoryCount[]): CategoryTreeNode[] {
  const roots: CategoryTreeNode[] = []
  const nodeMap = new Map<string, CategoryTreeNode>()

  for (const item of items) {
    const segments = splitCategorySegments(item.category)
    if (segments.length === 0) {
      continue
    }

    let parentPath = ''
    let currentLevel = roots

    segments.forEach((segment, index) => {
      const nodeId = parentPath ? `${parentPath} / ${segment}` : segment
      let node = nodeMap.get(nodeId)

      if (!node) {
        node = {
          id: nodeId,
          label: segment,
          count: 0,
          selfCount: 0,
          filterCategory: null,
          children: [],
        }
        nodeMap.set(nodeId, node)
        currentLevel.push(node)
      }

      node.count += item.count
      if (index === segments.length - 1) {
        node.selfCount += item.count
        node.filterCategory = item.category
      }

      parentPath = nodeId
      currentLevel = node.children
    })
  }

  const sortNodes = (nodes: CategoryTreeNode[]) => {
    nodes.sort((left, right) => {
      if (right.count !== left.count) {
        return right.count - left.count
      }
      return left.label.localeCompare(right.label)
    })
    nodes.forEach((node) => sortNodes(node.children))
  }

  sortNodes(roots)
  return roots
}

export function formatPublicDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function getDocumentTags(tags?: string) {
  return tags ? tags.split(',').map((tag) => tag.trim()).filter(Boolean).slice(0, 3) : []
}

export function buildLatestPlatformReleases(
  platformHistory?: PublicPlatformHistoryResponse,
  platformOverviewItems?: PublicPlatformOverviewItem[],
): PlatformReleasePreview[] {
  if (!platformHistory?.items) {
    return []
  }

  const platformIdByName = new Map<string, number>()
  for (const item of platformOverviewItems ?? []) {
    platformIdByName.set(normalizePlatformName(item.platform), item.id)
  }

  const releases: PlatformReleasePreview[] = []

  for (const platform of platformHistory.items) {
    let latestDoc: LatestPlatformRelease | null = null

    for (const category of platform.categories) {
      for (const yearGroup of category.years) {
        for (const doc of yearGroup.documents) {
          const docDate = doc.published_at || doc.updated_at
          if (!latestDoc) {
            latestDoc = {
              title: doc.title,
              documentNumber: doc.document_number,
              releaseBranch: doc.release_branch,
              versionLabel: doc.version_label,
              versionNumber: doc.version_number,
              publishedAt: docDate,
            }
          } else {
            const latestDate = latestDoc.publishedAt ? new Date(latestDoc.publishedAt).getTime() : 0
            const candidateDate = docDate ? new Date(docDate).getTime() : 0
            if (candidateDate > latestDate) {
              latestDoc = {
                title: doc.title,
                documentNumber: doc.document_number,
                releaseBranch: doc.release_branch,
                versionLabel: doc.version_label,
                versionNumber: doc.version_number,
                publishedAt: docDate,
              }
            }
          }
        }
      }
    }

    if (latestDoc) {
      releases.push({
        platformId: platformIdByName.get(normalizePlatformName(platform.platform)),
        platform: platform.platform,
        latestDoc,
      })
    }
  }

  return releases
    .sort((left, right) => {
      const leftDate = left.latestDoc.publishedAt ? new Date(left.latestDoc.publishedAt).getTime() : 0
      const rightDate = right.latestDoc.publishedAt
        ? new Date(right.latestDoc.publishedAt).getTime()
        : 0
      return rightDate - leftDate
    })
    .slice(0, 3)
}
