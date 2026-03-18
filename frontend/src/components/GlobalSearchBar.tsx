/**
 * GlobalSearchBar — Y2-001: Quick-search in header with dropdown results
 * Debounced API call, keyboard navigation, top-5 results as-you-type.
 */

import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, FileText, X, SlidersHorizontal } from 'lucide-react'
import { api } from '@/lib/api'
import AdvancedSearchModal from './AdvancedSearchModal'

interface QuickResult {
  id: number
  title: string
  document_number: string
  category: string | null
  status: string
}

export default function GlobalSearchBar() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<QuickResult[]>([])
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout>>()

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const doSearch = useCallback(async (q: string) => {
    if (q.length < 2) {
      setResults([])
      setSuggestions([])
      setIsOpen(false)
      return
    }
    setLoading(true)
    try {
      const res = await api.search(q, { pageSize: 5 })
      setResults(
        (res.items ?? []).slice(0, 5).map((item) => ({
          id: item.id,
          title: item.title,
          document_number: item.document_number,
          category: item.category,
          status: item.status,
        })),
      )
      setSuggestions(res.suggestions ?? [])
      setIsOpen(true)
    } catch {
      setResults([])
      setSuggestions([])
    } finally {
      setLoading(false)
    }
  }, [])

  const handleChange = (value: string) => {
    setQuery(value)
    setActiveIndex(-1)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => doSearch(value), 150)
  }

  const navigateToResult = (id: number) => {
    setIsOpen(false)
    setQuery('')
    navigate(`/documents/${id}`)
  }

  const navigateToFullSearch = () => {
    if (!query.trim()) return
    setIsOpen(false)
    navigate(`/documents?search=${encodeURIComponent(query.trim())}`)
    setQuery('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    const totalItems = results.length + (query.trim() ? 1 : 0) // +1 for "View all" row
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex((prev) => (prev < totalItems - 1 ? prev + 1 : 0))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex((prev) => (prev > 0 ? prev - 1 : totalItems - 1))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (activeIndex >= 0 && activeIndex < results.length) {
        navigateToResult(results[activeIndex].id)
      } else {
        navigateToFullSearch()
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false)
      inputRef.current?.blur()
    }
  }

  const hasResults = results.length > 0 || suggestions.length > 0

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => handleChange(e.target.value)}
          onFocus={() => query.length >= 2 && hasResults && setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder="Search documents..."
          className="w-44 rounded-full border border-sky-200 bg-white/80 py-1.5 pl-9 pr-8 text-sm text-slate-700 placeholder-slate-400 focus:border-sky-400 focus:outline-none focus:ring-1 focus:ring-sky-300 transition-all focus:w-64 max-w-[calc(100vw-8rem)]"
          aria-label="Search documents"
          role="combobox"
          aria-expanded={isOpen}
          aria-activedescendant={activeIndex >= 0 ? `search-result-${activeIndex}` : undefined}
        />
        {query && (
          <button
            onClick={() => { setQuery(''); setIsOpen(false); setResults([]) }}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            aria-label="Clear search"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* Advanced search trigger */}
      <button
        onClick={() => { setIsOpen(false); setShowAdvanced(true) }}
        className="ml-1 rounded-full p-1.5 text-slate-400 hover:bg-white/80 hover:text-slate-600"
        aria-label="Advanced search"
        title="Advanced search"
      >
        <SlidersHorizontal className="h-4 w-4" />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div
          className="absolute left-0 top-full z-50 mt-1 w-96 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl"
          role="listbox"
        >
          {loading && (
            <div className="px-4 py-3 text-center text-xs text-slate-400">Searching...</div>
          )}

          {!loading && results.length === 0 && query.length >= 2 && (
            <div className="px-4 py-4 text-center text-sm text-slate-400">
              No results for "{query}"
              {suggestions.length > 0 && (
                <div className="mt-2 text-xs">
                  Did you mean:{' '}
                  {suggestions.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => handleChange(s)}
                      className="text-sky-600 hover:underline"
                    >
                      {s}{i < suggestions.length - 1 ? ', ' : ''}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {!loading && results.length > 0 && (
            <>
              <div className="px-3 py-1.5 text-[10px] font-medium uppercase tracking-wider text-slate-400">
                Documents
              </div>
              {results.map((result, idx) => (
                <button
                  key={result.id}
                  id={`search-result-${idx}`}
                  role="option"
                  aria-selected={activeIndex === idx}
                  onClick={() => navigateToResult(result.id)}
                  className={`flex w-full items-start gap-3 px-3 py-2.5 text-left transition-colors ${
                    activeIndex === idx ? 'bg-sky-50 ring-2 ring-inset ring-sky-300' : 'hover:bg-slate-50'
                  }`}
                >
                  <FileText className="mt-0.5 h-4 w-4 flex-shrink-0 text-slate-400" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-900">{result.title}</p>
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <span>{result.document_number}</span>
                      {result.category && (
                        <>
                          <span>·</span>
                          <span>{result.category}</span>
                        </>
                      )}
                    </div>
                  </div>
                </button>
              ))}
              <button
                id={`search-result-${results.length}`}
                role="option"
                aria-selected={activeIndex === results.length}
                onClick={navigateToFullSearch}
                className={`w-full border-t border-slate-100 px-4 py-3 text-center text-sm font-semibold text-sky-600 transition-colors ${
                  activeIndex === results.length ? 'bg-sky-50 ring-2 ring-inset ring-sky-300' : 'hover:bg-sky-50'
                }`}
              >
                View all results for "{query}" →
              </button>
            </>
          )}
        </div>
      )}

      <AdvancedSearchModal
        isOpen={showAdvanced}
        onClose={() => setShowAdvanced(false)}
        initialQuery={query}
      />
    </div>
  )
}
