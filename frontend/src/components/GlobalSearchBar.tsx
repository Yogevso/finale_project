/**
 * GlobalSearchBar - Y2-001: Quick-search in header with dropdown results
 * Debounced API call, keyboard navigation, top-5 results as-you-type.
 */

import { useState, useRef, useEffect, useCallback, useId, type CSSProperties, type KeyboardEvent } from 'react'
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
  const resultsListId = useId()
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
  const searchSequenceRef = useRef(0)

  const closeDropdown = useCallback((options?: { blur?: boolean }) => {
    searchSequenceRef.current += 1
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
      debounceRef.current = undefined
    }
    setLoading(false)
    setIsOpen(false)
    setActiveIndex(-1)
    if (options?.blur) {
      inputRef.current?.blur()
    }
  }, [])

  const doSearch = useCallback(async (q: string, requestId: number) => {
    try {
      const res = await api.search(q, { pageSize: 5 })
      if (requestId !== searchSequenceRef.current) {
        return
      }

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
      if (requestId !== searchSequenceRef.current) {
        return
      }
      setResults([])
      setSuggestions([])
      setIsOpen(true)
    } finally {
      if (requestId === searchSequenceRef.current) {
        setLoading(false)
      }
    }
  }, [])

  // Close on outside click
  useEffect(() => {
    function handleClick(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        closeDropdown()
      }
    }

    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [closeDropdown])

  // Close on Escape even if focus moved while the popover is open.
  useEffect(() => {
    if (!isOpen) {
      return
    }

    function handleDocumentKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === 'Escape') {
        closeDropdown({ blur: true })
      }
    }

    document.addEventListener('keydown', handleDocumentKeyDown)
    return () => document.removeEventListener('keydown', handleDocumentKeyDown)
  }, [closeDropdown, isOpen])

  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
    }
  }, [])

  const handleChange = (value: string) => {
    setQuery(value)
    setActiveIndex(-1)

    searchSequenceRef.current += 1
    const requestId = searchSequenceRef.current

    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
      debounceRef.current = undefined
    }

    if (value.trim().length < 2) {
      setLoading(false)
      setResults([])
      setSuggestions([])
      setIsOpen(false)
      return
    }

    setLoading(true)
    setResults([])
    setSuggestions([])
    setIsOpen(true)
    debounceRef.current = setTimeout(() => {
      void doSearch(value, requestId)
    }, 150)
  }

  const navigateToResult = (id: number) => {
    closeDropdown()
    setQuery('')
    navigate(`/documents/${id}`)
  }

  const navigateToFullSearch = () => {
    if (!query.trim()) {
      return
    }

    closeDropdown()
    navigate(`/documents?search=${encodeURIComponent(query.trim())}`)
    setQuery('')
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape') {
      closeDropdown({ blur: true })
      return
    }

    const totalItems = results.length + (query.trim() ? 1 : 0)
    if (totalItems === 0) {
      return
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActiveIndex((prev) => (prev < totalItems - 1 ? prev + 1 : 0))
      return
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex((prev) => (prev > 0 ? prev - 1 : totalItems - 1))
      return
    }

    if (event.key === 'Enter') {
      event.preventDefault()
      if (activeIndex >= 0 && activeIndex < results.length) {
        navigateToResult(results[activeIndex].id)
      } else {
        navigateToFullSearch()
      }
    }
  }

  const clearSearch = () => {
    setQuery('')
    setResults([])
    setSuggestions([])
    closeDropdown()
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
          onChange={(event) => handleChange(event.target.value)}
          onFocus={() => query.trim().length >= 2 && (hasResults || loading) && setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder="Search documents..."
          className="max-w-[calc(100vw-8rem)] w-44 rounded-full border border-blue-200 bg-white/80 py-1.5 pl-9 pr-8 text-sm text-slate-700 placeholder-slate-400 transition-all focus:w-64 focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-300 dark:border-slate-700 dark:bg-slate-900/90 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:border-blue-400"
          aria-label="Search documents"
          role="combobox"
          aria-controls={resultsListId}
          aria-expanded={isOpen}
          aria-autocomplete="list"
          aria-activedescendant={activeIndex >= 0 ? `${resultsListId}-option-${activeIndex}` : undefined}
        />
        {query && (
          <button
            type="button"
            onClick={clearSearch}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-200"
            aria-label="Clear search"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      <button
        type="button"
        onClick={() => {
          closeDropdown()
          setShowAdvanced(true)
        }}
        className="ml-1 rounded-full p-1.5 text-slate-400 hover:bg-white/80 hover:text-slate-600 dark:text-slate-500 dark:hover:bg-slate-900 dark:hover:text-slate-200"
        aria-label="Advanced search"
        title="Advanced search"
      >
        <SlidersHorizontal className="h-4 w-4" />
      </button>

      {isOpen && (
        <div
          id={resultsListId}
          className="dropdown-menu motion-enter-slide absolute left-0 top-full z-50 mt-1 w-96 overflow-hidden dark:bg-slate-900"
          role="listbox"
        >
          {loading && (
            <div className="motion-enter-fade px-4 py-3 text-center text-xs text-slate-400 dark:text-slate-500">
              Searching...
            </div>
          )}

          {!loading && results.length === 0 && query.length >= 2 && (
            <div className="motion-enter-fade px-4 py-4 text-center text-sm text-slate-400 dark:text-slate-500">
              No results for "{query}"
              {suggestions.length > 0 && (
                <div className="mt-2 text-xs">
                  Did you mean:{' '}
                  {suggestions.map((suggestion, index) => (
                    <button
                      key={suggestion}
                      type="button"
                      onClick={() => handleChange(suggestion)}
                      className="text-blue-600 hover:underline dark:text-blue-300"
                    >
                      {suggestion}
                      {index < suggestions.length - 1 ? ', ' : ''}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {!loading && results.length > 0 && (
            <>
              <div className="motion-enter-fade px-3 py-1.5 text-[10px] font-medium uppercase tracking-wider text-slate-400 dark:text-slate-500">
                Documents
              </div>
              {results.map((result, index) => (
                <button
                  key={result.id}
                  id={`${resultsListId}-option-${index}`}
                  type="button"
                  role="option"
                  aria-selected={activeIndex === index}
                  onClick={() => navigateToResult(result.id)}
                  style={{ '--enter-delay': `${Math.min(index, 5) * 35}ms` } as CSSProperties}
                  className={`motion-enter-fade flex w-full items-start gap-3 px-3 py-2.5 text-left transition-colors ${
                    activeIndex === index
                      ? 'bg-blue-50 ring-2 ring-inset ring-blue-300 dark:bg-blue-950/30'
                      : 'hover:bg-slate-50 dark:hover:bg-slate-800'
                  }`}
                >
                  <FileText className="mt-0.5 h-4 w-4 flex-shrink-0 text-slate-400 dark:text-slate-500" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-900 dark:text-slate-100">{result.title}</p>
                    <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                      <span>{result.document_number}</span>
                      {result.category && (
                        <>
                          <span>&middot;</span>
                          <span>{result.category}</span>
                        </>
                      )}
                    </div>
                  </div>
                </button>
              ))}
              <button
                id={`${resultsListId}-option-${results.length}`}
                type="button"
                role="option"
                aria-selected={activeIndex === results.length}
                onClick={navigateToFullSearch}
                style={{ '--enter-delay': `${Math.min(results.length, 5) * 35}ms` } as CSSProperties}
                className={`motion-enter-fade w-full border-t border-slate-100 px-4 py-3 text-center text-sm font-semibold text-blue-600 transition-colors dark:border-slate-800 ${
                  activeIndex === results.length
                    ? 'bg-blue-50 ring-2 ring-inset ring-blue-300 dark:bg-blue-950/30'
                    : 'hover:bg-blue-50 dark:hover:bg-blue-950/30'
                }`}
              >
                View all results for "{query}" -&gt;
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
