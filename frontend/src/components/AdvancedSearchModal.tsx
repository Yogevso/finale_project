/**
 * AdvancedSearchModal — Y2-002: Advanced search query builder
 * Modal with fields: title, content, category, company, tag, date range, status, visibility.
 * Generates filter params and navigates to /documents with them.
 */

import { useState, useEffect, useId } from 'react'
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
  const titleId = useId()
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

  const { containerRef } = useFocusTrap(onClose)

  if (!isOpen) return null

  const categories = facetsQuery.data?.categories ?? []
  const statuses = facetsQuery.data?.statuses ?? []
  const companies = (companiesQuery.data as { items?: { id: number; name: string }[] })?.items ?? []

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
    <div className="modal-overlay flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0"
        onClick={onClose}
        aria-label="Close advanced search"
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="modal-content motion-enter-slide w-full max-w-lg dark:bg-slate-900"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="h-5 w-5 text-blue-600 dark:text-blue-300" />
            <h2 id={titleId} className="text-lg font-semibold text-slate-900 dark:text-slate-100">Advanced Search</h2>
          </div>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-200" aria-label="Close advanced search">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form */}
        <div className="space-y-4 p-6">
          {/* Text query */}
          <div>
            <label htmlFor="adv-search-query" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">Search text</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400 dark:text-slate-500" />
              <input
                id="adv-search-query"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Title or content keywords..."
                className="input-field py-2 pl-9 pr-3"
              />
            </div>
          </div>

          {/* Two-column grid */}
          <div className="grid grid-cols-2 gap-4">
            {/* Category */}
            <div>
              <label htmlFor="adv-search-category" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">Category</label>
              <select
                id="adv-search-category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="select-field"
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
              <label htmlFor="adv-search-status" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">Status</label>
              <select
                id="adv-search-status"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="select-field"
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
              <label htmlFor="adv-search-visibility" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">Visibility</label>
              <select
                id="adv-search-visibility"
                value={visibility}
                onChange={(e) => setVisibility(e.target.value)}
                className="select-field"
              >
                <option value="">Any visibility</option>
                <option value="internal">Internal</option>
                <option value="customer">Customer</option>
                <option value="public">Public</option>
              </select>
            </div>

            {/* Company */}
            <div>
              <label htmlFor="adv-search-company" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">Company</label>
              <select
                id="adv-search-company"
                value={companyId}
                onChange={(e) => setCompanyId(e.target.value)}
                disabled={companiesQuery.isLoading}
                className="select-field disabled:opacity-60"
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
              <label htmlFor="adv-search-date-from" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">Created after</label>
              <input
                id="adv-search-date-from"
                type="date"
                value={dateFrom}
                max={dateTo || undefined}
                onChange={(e) => setDateFrom(e.target.value)}
                className="input-field"
              />
            </div>

            {/* Date to */}
            <div>
              <label htmlFor="adv-search-date-to" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">Created before</label>
              <input
                id="adv-search-date-to"
                type="date"
                value={dateTo}
                min={dateFrom || undefined}
                onChange={(e) => setDateTo(e.target.value)}
                className="input-field"
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-200 px-6 py-4 dark:border-slate-800">
          <button type="button" onClick={handleReset} className="text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200">
            Reset filters
          </button>
          <div className="flex items-center gap-3">
            {activeFilterCount > 0 && (
              <span className="text-xs text-slate-400 dark:text-slate-500">{activeFilterCount} filter(s) active</span>
            )}
            <button type="button" onClick={onClose} className="btn-ghost">
              Cancel
            </button>
            <button type="button" onClick={handleSearch} className="btn-primary flex items-center gap-2">
              <Search className="h-4 w-4" /> Search
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
