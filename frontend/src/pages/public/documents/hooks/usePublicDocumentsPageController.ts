import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'

import { publicApi } from '@/lib/publicApi'

import {
  buildCategoryTree,
  buildLatestPlatformReleases,
  splitCategorySegments,
} from '../lib/catalog'

export function usePublicDocumentsPageController() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [localSearch, setLocalSearch] = useState('')
  const [expandedCategoryIds, setExpandedCategoryIds] = useState<string[]>([])

  const page = Number.parseInt(searchParams.get('page') || '1', 10)
  const category = searchParams.get('category') || undefined
  const search = searchParams.get('search') || undefined

  useEffect(() => {
    setLocalSearch(search || '')
  }, [search])

  const docsQuery = useQuery({
    queryKey: ['public-documents', { page, page_size: 12, category, search }],
    queryFn: () => publicApi.getDocuments({ page, page_size: 12, category, search }),
  })

  const categoriesQuery = useQuery({
    queryKey: ['public-categories'],
    queryFn: () => publicApi.getCategories(),
  })

  const platformHistoryQuery = useQuery({
    queryKey: ['public-platform-history-preview'],
    queryFn: () => publicApi.getPlatformHistory(),
  })

  const platformOverviewQuery = useQuery({
    queryKey: ['public-platform-overview-preview'],
    queryFn: () => publicApi.getPlatformsOverview(),
  })

  const sortedCategories = useMemo(() => {
    const items = categoriesQuery.data?.items || []
    return [...items].sort((left, right) => {
      if (right.count !== left.count) {
        return right.count - left.count
      }
      return left.category.localeCompare(right.category)
    })
  }, [categoriesQuery.data?.items])

  const totalCategoryDocuments = useMemo(
    () => sortedCategories.reduce((sum, item) => sum + item.count, 0),
    [sortedCategories],
  )

  const categoryTree = useMemo(() => buildCategoryTree(sortedCategories), [sortedCategories])

  useEffect(() => {
    if (!category) {
      return
    }

    const nextExpanded = splitCategorySegments(category).reduce<string[]>((paths, segment) => {
      const previous = paths[paths.length - 1]
      paths.push(previous ? `${previous} / ${segment}` : segment)
      return paths
    }, [])

    setExpandedCategoryIds((previous) => Array.from(new Set([...previous, ...nextExpanded])))
  }, [category])

  const latestPlatformReleases = useMemo(
    () =>
      buildLatestPlatformReleases(platformHistoryQuery.data, platformOverviewQuery.data?.items),
    [platformHistoryQuery.data, platformOverviewQuery.data?.items],
  )

  const handleCategoryClick = (nextCategory: string | null) => {
    const params = new URLSearchParams(searchParams)
    if (nextCategory) {
      params.set('category', nextCategory)
    } else {
      params.delete('category')
    }
    params.set('page', '1')
    setSearchParams(params)
  }

  const handlePageChange = (newPage: number) => {
    const params = new URLSearchParams(searchParams)
    params.set('page', newPage.toString())
    setSearchParams(params)
  }

  const handleLocalSearchSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    const params = new URLSearchParams(searchParams)
    if (localSearch.trim()) {
      params.set('search', localSearch.trim())
    } else {
      params.delete('search')
    }
    params.set('page', '1')
    setSearchParams(params)
  }

  const clearSearch = () => {
    const params = new URLSearchParams(searchParams)
    params.delete('search')
    params.set('page', '1')
    setSearchParams(params)
    setLocalSearch('')
  }

  const clearAllFilters = () => {
    setSearchParams({})
    setLocalSearch('')
  }

  const toggleCategoryNode = (categoryId: string) => {
    setExpandedCategoryIds((previous) =>
      previous.includes(categoryId)
        ? previous.filter((value) => value !== categoryId)
        : [...previous, categoryId],
    )
  }

  return {
    category,
    categoryTree,
    clearAllFilters,
    clearSearch,
    docsQuery,
    expandedCategoryIds,
    handleCategoryClick,
    handleLocalSearchSubmit,
    handlePageChange,
    latestPlatformReleases,
    localSearch,
    page,
    search,
    setLocalSearch,
    setViewMode,
    toggleCategoryNode,
    totalCategoryDocuments,
    viewMode,
  }
}
