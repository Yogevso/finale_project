import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Building2, Check, Search, X } from 'lucide-react'

import { api } from '@/lib/api'
import { queryKeys } from '@/lib/queryKeys'
import type { Company, CompanyType } from '@/types'

type SelectorCompany = Pick<Company, 'id' | 'name' | 'slug' | 'company_type'>

interface CompanySelectorProps {
  selectedIds: number[]
  onChange: (ids: number[]) => void
  disabled?: boolean
  placeholder?: string
  noResultsText?: string
  loadingText?: string
  errorText?: string
  companyType?: CompanyType
  activeOnly?: boolean
  perPage?: number
  className?: string
  selectedCompanyOptions?: SelectorCompany[]
}

const DEFAULT_PLACEHOLDER = 'Select companies...'
const DEFAULT_NO_RESULTS_TEXT = 'No companies found'
const DEFAULT_LOADING_TEXT = 'Loading companies...'
const DEFAULT_ERROR_TEXT = 'Failed to load companies'
const SEARCH_DEBOUNCE_MS = 250

const getCompanyTypeBadgeClassName = (companyType: CompanyType) => {
  if (companyType === 'customer') {
    return 'bg-sky-100 text-sky-700'
  }
  if (companyType === 'partner') {
    return 'bg-indigo-100 text-indigo-700'
  }
  return 'bg-emerald-100 text-emerald-700'
}

function mergeCompanies(
  base: Record<number, SelectorCompany>,
  companies: SelectorCompany[] | undefined,
): Record<number, SelectorCompany> {
  if (!companies || companies.length === 0) {
    return base
  }

  const next = { ...base }
  for (const company of companies) {
    next[company.id] = company
  }
  return next
}

export default function CompanySelector({
  selectedIds,
  onChange,
  disabled = false,
  placeholder = DEFAULT_PLACEHOLDER,
  noResultsText = DEFAULT_NO_RESULTS_TEXT,
  loadingText = DEFAULT_LOADING_TEXT,
  errorText = DEFAULT_ERROR_TEXT,
  companyType,
  activeOnly = true,
  perPage = 25,
  className = '',
  selectedCompanyOptions,
}: CompanySelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchInput, setSearchInput] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [page, setPage] = useState(1)
  const [activeOptionIndex, setActiveOptionIndex] = useState(-1)
  const [knownCompaniesById, setKnownCompaniesById] = useState<Record<number, SelectorCompany>>({})
  const selectorRootRef = useRef<HTMLDivElement | null>(null)
  const triggerButtonRef = useRef<HTMLButtonElement | null>(null)
  const searchInputRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setSearchQuery(searchInput.trim())
    }, SEARCH_DEBOUNCE_MS)
    return () => window.clearTimeout(timeout)
  }, [searchInput])

  useEffect(() => {
    setPage(1)
  }, [searchQuery, companyType, activeOnly, perPage])

  const companiesQuery = useQuery({
    queryKey: queryKeys.companies.selector({
      page,
      per_page: perPage,
      search: searchQuery || undefined,
      company_type: companyType,
      is_active: activeOnly,
    }),
    queryFn: () =>
      api.getCompanies({
        page,
        per_page: perPage,
        search: searchQuery || undefined,
        company_type: companyType,
        is_active: activeOnly,
      }),
    placeholderData: (previous) => previous,
  })

  const pageCompanies = companiesQuery.data?.items || []
  const currentPage = companiesQuery.data?.page ?? page
  const totalPages = companiesQuery.data?.pages ?? 1
  const hasPreviousPage = currentPage > 1
  const hasNextPage = currentPage < totalPages

  useEffect(() => {
    setKnownCompaniesById((previous) => mergeCompanies(previous, selectedCompanyOptions))
  }, [selectedCompanyOptions])

  useEffect(() => {
    setKnownCompaniesById((previous) => mergeCompanies(previous, pageCompanies))
  }, [pageCompanies])

  const selectedCompanies = useMemo(
    () =>
      selectedIds
        .map((companyId) => knownCompaniesById[companyId])
        .filter((company): company is SelectorCompany => Boolean(company)),
    [knownCompaniesById, selectedIds],
  )

  const toggleCompany = (companyId: number) => {
    if (selectedIds.includes(companyId)) {
      onChange(selectedIds.filter((id) => id !== companyId))
      return
    }
    onChange([...selectedIds, companyId])
  }

  const removeCompany = (companyId: number) => {
    onChange(selectedIds.filter((id) => id !== companyId))
  }

  const clearAllCompanies = () => {
    if (selectedIds.length === 0) {
      return
    }
    onChange([])
  }

  const closeDropdown = (focusTrigger = false) => {
    setIsOpen(false)
    if (focusTrigger) {
      window.setTimeout(() => {
        triggerButtonRef.current?.focus()
      }, 0)
    }
  }

  const openDropdown = (preferredIndex?: number) => {
    setIsOpen(true)
    if (typeof preferredIndex === 'number') {
      setActiveOptionIndex(preferredIndex)
    }
  }

  const moveActiveOption = (delta: number) => {
    if (pageCompanies.length === 0) {
      return
    }

    setActiveOptionIndex((previous) => {
      if (previous < 0 || previous >= pageCompanies.length) {
        return delta > 0 ? 0 : pageCompanies.length - 1
      }
      return (previous + delta + pageCompanies.length) % pageCompanies.length
    })
  }

  const selectActiveOption = () => {
    if (activeOptionIndex < 0 || activeOptionIndex >= pageCompanies.length) {
      return
    }
    toggleCompany(pageCompanies[activeOptionIndex].id)
  }

  const handleTriggerKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (disabled) {
      return
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault()
      openDropdown(pageCompanies.length > 0 ? 0 : -1)
      return
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault()
      openDropdown(pageCompanies.length > 0 ? pageCompanies.length - 1 : -1)
      return
    }

    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      openDropdown()
      return
    }

    if (event.key === 'Escape') {
      event.preventDefault()
      closeDropdown()
    }
  }

  const handleSearchInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      moveActiveOption(1)
      return
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault()
      moveActiveOption(-1)
      return
    }

    if (event.key === 'Home') {
      if (pageCompanies.length > 0) {
        event.preventDefault()
        setActiveOptionIndex(0)
      }
      return
    }

    if (event.key === 'End') {
      if (pageCompanies.length > 0) {
        event.preventDefault()
        setActiveOptionIndex(pageCompanies.length - 1)
      }
      return
    }

    if (event.key === 'Enter') {
      if (activeOptionIndex >= 0) {
        event.preventDefault()
        selectActiveOption()
      }
      return
    }

    if (event.key === 'Escape') {
      event.preventDefault()
      closeDropdown(true)
    }
  }

  useEffect(() => {
    if (disabled && isOpen) {
      setIsOpen(false)
      return
    }

    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node | null
      if (!target || !selectorRootRef.current?.contains(target)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [disabled, isOpen])

  useEffect(() => {
    if (!isOpen || disabled) {
      return
    }
    window.setTimeout(() => {
      searchInputRef.current?.focus()
    }, 0)
  }, [disabled, isOpen])

  useEffect(() => {
    if (!isOpen) {
      return
    }

    if (pageCompanies.length === 0) {
      setActiveOptionIndex(-1)
      return
    }

    setActiveOptionIndex((previous) => {
      if (previous >= 0 && previous < pageCompanies.length) {
        return previous
      }
      const selectedOptionIndex = pageCompanies.findIndex((company) =>
        selectedIds.includes(company.id),
      )
      return selectedOptionIndex >= 0 ? selectedOptionIndex : 0
    })
  }, [isOpen, pageCompanies, selectedIds])

  const activeCompany = activeOptionIndex >= 0 ? pageCompanies[activeOptionIndex] : undefined
  const activeDescendantId = activeCompany
    ? `company-selector-option-${activeCompany.id}`
    : undefined

  const triggerLabel =
    selectedIds.length === 0
      ? placeholder
      : `${selectedIds.length} ${selectedIds.length === 1 ? 'company' : 'companies'} selected`

  return (
    <div
      ref={selectorRootRef}
      className={`relative ${className}`.trim()}
      data-testid="company-selector"
    >
      {selectedIds.length > 0 && (
        <div className="mb-2 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-500">
              {selectedIds.length} {selectedIds.length === 1 ? 'company' : 'companies'} selected
            </p>
            {!disabled && (
              <button
                type="button"
                onClick={clearAllCompanies}
                className="text-xs font-medium text-rose-600 hover:text-rose-700"
                data-testid="company-selector-clear-all"
              >
                Clear all
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {selectedCompanies.map((company) => (
              <span
                key={company.id}
                className="inline-flex items-center gap-1 px-2 py-1 bg-sky-100 text-sky-700 rounded-full text-sm"
              >
                <Building2 className="w-3 h-3" />
                {company.name}
                {!disabled && (
                  <button
                    type="button"
                    onClick={() => removeCompany(company.id)}
                    className="ml-1 hover:bg-sky-200 rounded-full p-0.5"
                    data-testid={`company-selector-remove-${company.id}`}
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </span>
            ))}
          </div>
        </div>
      )}

      <button
        ref={triggerButtonRef}
        type="button"
        onClick={() => {
          if (isOpen) {
            closeDropdown()
            return
          }
          openDropdown()
        }}
        onKeyDown={handleTriggerKeyDown}
        className="w-full px-3 py-2 border border-slate-300 rounded-xl text-left text-slate-600 hover:border-slate-400 focus:ring-2 focus:ring-sky-500 focus:border-sky-500 disabled:opacity-60 disabled:cursor-not-allowed"
        disabled={disabled}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-controls="company-selector-listbox"
        data-testid="company-selector-trigger"
      >
        {triggerLabel}
      </button>

      {isOpen && (
        <div className="absolute z-10 mt-1 w-full bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden">
          <div className="p-2 border-b border-slate-200">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                ref={searchInputRef}
                type="text"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                onKeyDown={handleSearchInputKeyDown}
                placeholder="Search companies..."
                className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-sky-500"
                role="combobox"
                aria-autocomplete="list"
                aria-controls="company-selector-listbox"
                aria-expanded={isOpen}
                aria-activedescendant={activeDescendantId}
                data-testid="company-selector-search"
              />
            </div>
          </div>

          <div className="max-h-48 overflow-y-auto" role="listbox" id="company-selector-listbox">
            {companiesQuery.isLoading ? (
              <div className="px-4 py-3 text-slate-500 text-sm" data-testid="company-selector-loading">
                {loadingText}
              </div>
            ) : companiesQuery.isError ? (
              <div className="px-4 py-3 text-rose-600 text-sm" data-testid="company-selector-error">
                {errorText}
              </div>
            ) : pageCompanies.length === 0 ? (
              <div className="px-4 py-3 text-slate-500 text-sm" data-testid="company-selector-no-results">
                {noResultsText}
              </div>
            ) : (
              pageCompanies.map((company, index) => (
                <button
                  id={`company-selector-option-${company.id}`}
                  key={company.id}
                  type="button"
                  role="option"
                  aria-selected={selectedIds.includes(company.id)}
                  onClick={() => {
                    setActiveOptionIndex(index)
                    toggleCompany(company.id)
                  }}
                  onMouseEnter={() => setActiveOptionIndex(index)}
                  onFocus={() => setActiveOptionIndex(index)}
                  className={`w-full flex items-center gap-3 px-4 py-2 text-left ${
                    activeOptionIndex === index ? 'bg-sky-50' : 'hover:bg-slate-50'
                  }`}
                  data-testid={`company-selector-option-${company.id}`}
                >
                  <div
                    className={`w-5 h-5 rounded border flex items-center justify-center ${
                      selectedIds.includes(company.id)
                        ? 'bg-sky-600 border-sky-600'
                        : 'border-slate-300'
                    }`}
                  >
                    {selectedIds.includes(company.id) && <Check className="w-3 h-3 text-white" />}
                  </div>
                  <div className="flex-1">
                    <div className="font-medium text-slate-900">{company.name}</div>
                    <div className="text-xs text-slate-500">{company.slug}</div>
                  </div>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${getCompanyTypeBadgeClassName(company.company_type)}`}
                  >
                    {company.company_type}
                  </span>
                </button>
              ))
            )}
          </div>

          {(totalPages > 1 || companiesQuery.isFetching) && (
            <div className="px-3 py-2 border-t border-slate-200 flex items-center justify-between text-xs text-slate-600 bg-slate-50">
              <div data-testid="company-selector-page-indicator">
                Page {currentPage} of {Math.max(totalPages, 1)}
                {companiesQuery.isFetching ? ' - Updating...' : ''}
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="px-2 py-1 rounded border border-slate-300 disabled:opacity-40"
                  onClick={() => setPage((previous) => Math.max(1, previous - 1))}
                  disabled={!hasPreviousPage || companiesQuery.isFetching}
                  data-testid="company-selector-prev-page"
                >
                  Prev
                </button>
                <button
                  type="button"
                  className="px-2 py-1 rounded border border-slate-300 disabled:opacity-40"
                  onClick={() => setPage((previous) => previous + 1)}
                  disabled={!hasNextPage || companiesQuery.isFetching}
                  data-testid="company-selector-next-page"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
