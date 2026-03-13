import type { DocumentStatus, DocumentVisibility, SavedSearch } from '@/types'

export interface DocumentsSavedViewState {
  search: string
  statusFilter: DocumentStatus | ''
  visibilityFilter: DocumentVisibility | ''
  categoryFilter: string
  companyIdFilter: number | null
  dateFrom: string
  dateTo: string
}

interface SavedViewPayload {
  version: 1
  search: string
  statusFilter: DocumentStatus | ''
  visibilityFilter: DocumentVisibility | ''
  categoryFilter: string
  companyIdFilter: number | null
  dateFrom: string
  dateTo: string
}

export interface SavedDocumentsView {
  id: number
  name: string
  filters: DocumentsSavedViewState
  createdAt: string
}

export function buildSavedViewPayload(filters: DocumentsSavedViewState) {
  const payload: SavedViewPayload = {
    version: 1,
    search: filters.search,
    statusFilter: filters.statusFilter,
    visibilityFilter: filters.visibilityFilter,
    categoryFilter: filters.categoryFilter,
    companyIdFilter: filters.companyIdFilter,
    dateFrom: filters.dateFrom,
    dateTo: filters.dateTo,
  }

  return {
    query: JSON.stringify(payload),
    category: filters.categoryFilter || undefined,
    date_from: filters.dateFrom || null,
    date_to: filters.dateTo || null,
  }
}

export function parseSavedDocumentsView(savedSearch: SavedSearch): SavedDocumentsView {
  const fallbackFilters: DocumentsSavedViewState = {
    search: savedSearch.query || '',
    statusFilter: '',
    visibilityFilter: '',
    categoryFilter: savedSearch.category || '',
    companyIdFilter: null,
    dateFrom: savedSearch.date_from || '',
    dateTo: savedSearch.date_to || '',
  }

  try {
    const parsed = savedSearch.query ? (JSON.parse(savedSearch.query) as Partial<SavedViewPayload>) : null
    if (!parsed || parsed.version !== 1) {
      return {
        id: savedSearch.id,
        name: savedSearch.name,
        filters: fallbackFilters,
        createdAt: savedSearch.created_at,
      }
    }

    return {
      id: savedSearch.id,
      name: savedSearch.name,
      filters: {
        search: parsed.search || '',
        statusFilter: parsed.statusFilter || '',
        visibilityFilter: parsed.visibilityFilter || '',
        categoryFilter: parsed.categoryFilter || savedSearch.category || '',
        companyIdFilter:
          typeof parsed.companyIdFilter === 'number' && parsed.companyIdFilter > 0
            ? parsed.companyIdFilter
            : null,
        dateFrom: parsed.dateFrom || savedSearch.date_from || '',
        dateTo: parsed.dateTo || savedSearch.date_to || '',
      },
      createdAt: savedSearch.created_at,
    }
  } catch {
    return {
      id: savedSearch.id,
      name: savedSearch.name,
      filters: fallbackFilters,
      createdAt: savedSearch.created_at,
    }
  }
}
