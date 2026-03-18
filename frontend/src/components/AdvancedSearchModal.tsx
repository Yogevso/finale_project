/**
 * AdvancedSearchModal — Y2-002: Advanced search query builder
 * Modal with fields: title, content, category, company, tag, date range, status, visibility.
 * Generates filter params and navigates to /documents with them.
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { X, Search, SlidersHorizontal } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useFocusTrap } from '@/hooks/useAccessibility'

interface AdvancedSearchModalProps {
  isOpen: boolean
  onClose: () => void
  initialQuery?: string
}

export default function AdvancedSearchModal({ isOpen, onClose, initialQuery = '' }: AdvancedSearchModalProps) {
  const navigate = useNavigate()
  const [query, setQuery] = useState(initialQuery)
  const [category, setCategory] = useState('')
  const [status, setStatus] = useState('')
  const [visibility, setVisibility] = useState('')
  const [companyId, setCompanyId] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  // Fetch facets for category options
  const facetsQuery = useQuery({
    queryKey: ['searchFacets'],
    queryFn: () => api.getSearchFacets(),
    enabled: isOpen,
  })

  // Fetch companies for company filter
  const companiesQuery = useQuery({
    queryKey: ['companies'],
    queryFn: () => api.getCompanies(),
    enabled: isOpen,
  })

  useEffect(() => {
    if (initialQuery) setQuery(initialQuery)
  }, [initialQuery])

  if (!isOpen) return null

  const categories = facetsQuery.data?.categories ?? []
  const statuses = facetsQuery.data?.statuses ?? []
  const companies = (companiesQuery.data as { items?: { id: number; name: string }[] })?.items ?? []

  const { containerRef, handleKeyDown } = useFocusTrap(onClose)

  const handleSearch = () => {
    const params = new URLSearchParams()
    if (query.trim()) params.set('search', query.trim())
    if (category) params.set('category', category)
    if (status) params.set('status', status)
    if (visibility) params.set('visibility', visibility)
    if (companyId) params.set('company', companyId)
    if (dateFrom) params.set('from', dateFrom)
    if (dateTo) params.set('to', dateTo)

    navigate(`/documents?${params.toString()}`)
    onClose()
  }

  const handleReset = () => {
    setQuery('')
    setCategory('')
    setStatus('')
    setVisibility('')
    setCompanyId('')
    setDateFrom('')
    setDateTo('')
  }

  const activeFilterCount = [query, category, status, visibility, companyId, dateFrom, dateTo].filter(Boolean).length

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-label="Advanced Search"
        className="w-full max-w-lg rounded-2xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="h-5 w-5 text-sky-600" />
            <h2 className="text-lg font-semibold text-gray-900">Advanced Search</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600" aria-label="Close advanced search">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form */}
        <div className="space-y-4 p-6">
          {/* Text query */}
          <div>
            <label htmlFor="adv-search-query" className="mb-1 block text-sm font-medium text-gray-700">Search text</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                id="adv-search-query"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Title or content keywords..."
                className="w-full rounded-lg border border-gray-300 py-2 pl-9 pr-3 text-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-300"
                autoFocus
              />
            </div>
          </div>

          {/* Two-column grid */}
          <div className="grid grid-cols-2 gap-4">
            {/* Category */}
            <div>
              <label htmlFor="adv-search-category" className="mb-1 block text-sm font-medium text-gray-700">Category</label>
              <select
                id="adv-search-category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
              >
                <option value="">Any category</option>
                {categories.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.name} ({c.count})
                  </option>
                ))}
              </select>
            </div>

            {/* Status */}
            <div>
              <label htmlFor="adv-search-status" className="mb-1 block text-sm font-medium text-gray-700">Status</label>
              <select
                id="adv-search-status"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
              >
                <option value="">Any status</option>
                {statuses.map((s) => (
                  <option key={s.name} value={s.name}>
                    {s.name} ({s.count})
                  </option>
                ))}
              </select>
            </div>

            {/* Visibility */}
            <div>
              <label htmlFor="adv-search-visibility" className="mb-1 block text-sm font-medium text-gray-700">Visibility</label>
              <select
                id="adv-search-visibility"
                value={visibility}
                onChange={(e) => setVisibility(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
              >
                <option value="">Any visibility</option>
                <option value="internal">Internal</option>
                <option value="customer">Customer</option>
                <option value="public">Public</option>
              </select>
            </div>

            {/* Company */}
            <div>
              <label htmlFor="adv-search-company" className="mb-1 block text-sm font-medium text-gray-700">Company</label>
              <select
                id="adv-search-company"
                value={companyId}
                onChange={(e) => setCompanyId(e.target.value)}
                disabled={companiesQuery.isLoading}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none disabled:opacity-60"
              >
                <option value="">{companiesQuery.isLoading ? 'Loading companies…' : 'Any company'}</option>
                {companies.map((c) => (
                  <option key={c.id} value={String(c.id)}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Date from */}
            <div>
              <label htmlFor="adv-search-date-from" className="mb-1 block text-sm font-medium text-gray-700">Created after</label>
              <input
                id="adv-search-date-from"
                type="date"
                value={dateFrom}
                max={dateTo || undefined}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
              />
            </div>

            {/* Date to */}
            <div>
              <label htmlFor="adv-search-date-to" className="mb-1 block text-sm font-medium text-gray-700">Created before</label>
              <input
                id="adv-search-date-to"
                type="date"
                value={dateTo}
                min={dateFrom || undefined}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-gray-200 px-6 py-4">
          <button onClick={handleReset} className="text-sm text-gray-500 hover:text-gray-700">
            Reset filters
          </button>
          <div className="flex items-center gap-3">
            {activeFilterCount > 0 && (
              <span className="text-xs text-gray-400">{activeFilterCount} filter(s) active</span>
            )}
            <button onClick={onClose} className="btn-ghost">
              Cancel
            </button>
            <button onClick={handleSearch} className="btn-primary flex items-center gap-2">
              <Search className="h-4 w-4" /> Search
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
