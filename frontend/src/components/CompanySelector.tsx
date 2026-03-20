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
const EMPTY_PAGE_COMPANIES: SelectorCompany[] = []

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

  const pageCompanies = companiesQuery.data?.items ?? EMPTY_PAGE_COMPANIES
  const currentPage = companiesQuery.data?.page ?? page
  const totalPages = companiesQuery.data?.total_pages ?? 1
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
      {selectedIds.length > 0 ? (
        <div className="mb-2 space-y-2">
          <div className="flex items-center justify-between">
            <p className="helper-copy">
              {selectedIds.length} {selectedIds.length === 1 ? 'company' : 'companies'} selected
            </p>
            {!disabled ? (
              <button
                type="button"
                onClick={clearAllCompanies}
                className="btn-ghost table-action-btn !px-0 text-rose-600 hover:bg-transparent hover:text-rose-700"
                data-testid="company-selector-clear-all"
              >
                Clear all
              </button>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-2">
            {selectedCompanies.map((company) => (
              <span
                key={company.id}
                className="inline-flex items-center gap-1 rounded-full bg-sky-100 px-2.5 py-1 text-sm text-sky-700 dark:bg-sky-950/40 dark:text-sky-200"
              >
                <Building2 className="w-3 h-3" />
                {company.name}
                {!disabled ? (
                  <button
                    type="button"
                    onClick={() => removeCompany(company.id)}
                    className="btn-icon ml-1 h-6 w-6 border-0 bg-transparent text-sky-700 shadow-none hover:bg-sky-200 hover:text-sky-900 dark:hover:bg-sky-900/50 dark:hover:text-sky-100"
                    data-testid={`company-selector-remove-${company.id}`}
                    aria-label={`Remove ${company.name}`}
                  >
                    <X className="w-3 h-3" />
                  </button>
                ) : null}
              </span>
            ))}
          </div>
        </div>
      ) : null}

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
        className="input-field body-copy text-left hover:border-slate-400 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={disabled}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-controls="company-selector-listbox"
        data-testid="company-selector-trigger"
      >
        {triggerLabel}
      </button>

      {isOpen ? (
        <div className="dropdown-menu absolute z-[60] mt-1 w-full overflow-hidden">
          <div className="border-b border-slate-200 p-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                ref={searchInputRef}
                type="text"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                onKeyDown={handleSearchInputKeyDown}
                placeholder="Search companies..."
                className="input-field pl-9 pr-3"
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
              <div className="body-copy px-4 py-3" data-testid="company-selector-loading">
                {loadingText}
              </div>
            ) : companiesQuery.isError ? (
              <div className="body-copy px-4 py-3 text-rose-600" data-testid="company-selector-error">
                {errorText}
              </div>
            ) : pageCompanies.length === 0 ? (
              <div className="body-copy px-4 py-3" data-testid="company-selector-no-results">
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
                  onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    setActiveOptionIndex(index)
                    toggleCompany(company.id)
                  }}
                  onMouseDown={(e) => {
                    e.stopPropagation()
                  }}
                  onMouseEnter={() => setActiveOptionIndex(index)}
                  onFocus={() => setActiveOptionIndex(index)}
                  className={`w-full px-4 py-2 text-left ${
                    activeOptionIndex === index
                      ? 'bg-sky-50 dark:bg-sky-950/40'
                      : 'hover:bg-slate-50 dark:hover:bg-slate-900'
                  }`}
                  data-testid={`company-selector-option-${company.id}`}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`flex h-5 w-5 items-center justify-center rounded border ${
                        selectedIds.includes(company.id)
                          ? 'border-sky-600 bg-sky-600'
                          : 'border-slate-300'
                      }`}
                    >
                      {selectedIds.includes(company.id) ? (
                        <Check className="w-3 h-3 text-white" />
                      ) : null}
                    </div>
                    <div className="flex-1">
                      <div className="card-title text-sm">{company.name}</div>
                      <div className="helper-copy">{company.slug}</div>
                    </div>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${getCompanyTypeBadgeClassName(company.company_type)}`}
                    >
                      {company.company_type}
                    </span>
                  </div>
                </button>
              ))
            )}
          </div>

          {totalPages > 1 || companiesQuery.isFetching ? (
            <div className="surface-muted rounded-none border-0 border-t border-slate-200 px-3 py-2">
              <div className="flex items-center justify-between gap-3">
                <div className="helper-copy" data-testid="company-selector-page-indicator">
                  Page {currentPage} of {Math.max(totalPages, 1)}
                  {companiesQuery.isFetching ? ' - Updating...' : ''}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    className="btn-ghost table-action-btn disabled:opacity-40"
                    onClick={() => setPage((previous) => Math.max(1, previous - 1))}
                    disabled={!hasPreviousPage || companiesQuery.isFetching}
                    data-testid="company-selector-prev-page"
                  >
                    Prev
                  </button>
                  <button
                    type="button"
                    className="btn-ghost table-action-btn disabled:opacity-40"
                    onClick={() => setPage((previous) => previous + 1)}
                    disabled={!hasNextPage || companiesQuery.isFetching}
                    data-testid="company-selector-next-page"
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
