import { useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/lib/auth'
import { api } from '@/lib/api'
import { Building2, Search, Plus, Users, FileText, MoreVertical, Eye, Trash2, Edit } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { Company, CompanyType } from '@/types'
import CompanyForm from '@/components/CompanyForm'
import ConfirmationDialog from '@/components/ConfirmationDialog'
import PageHeader from '@/components/PageHeader'

export default function CompaniesPage() {
  const { isAdmin } = useAuth()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [activeFilter, setActiveFilter] = useState<string>('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingCompany, setEditingCompany] = useState<Company | null>(null)
  const [openDropdown, setOpenDropdown] = useState<number | null>(null)
  const [companyToDeactivate, setCompanyToDeactivate] = useState<Company | null>(null)
  const actionMenuRef = useRef<HTMLDivElement>(null)
  const actionTriggerRefs = useRef<Record<number, HTMLButtonElement | null>>({})
  const previousOpenDropdownRef = useRef<number | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['companies', page, search, typeFilter, activeFilter],
    queryFn: () => api.getCompanies({
      page,
      per_page: 20,
      search: search || undefined,
      company_type: typeFilter || undefined,
      is_active: activeFilter ? activeFilter === 'true' : undefined,
    }),
    enabled: isAdmin,
  })

  const deleteCompanyMutation = useMutation({
    mutationFn: (id: number) => api.deleteCompany(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companies'] })
    },
  })

  useEffect(() => {
    if (openDropdown !== null) {
      requestAnimationFrame(() => {
        actionMenuRef.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus()
      })
    } else if (previousOpenDropdownRef.current !== null) {
      actionTriggerRefs.current[previousOpenDropdownRef.current]?.focus()
    }

    previousOpenDropdownRef.current = openDropdown
  }, [openDropdown])

  useEffect(() => {
    if (openDropdown === null) {
      return
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpenDropdown(null)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [openDropdown])

  const handleDeleteCompany = (company: Company) => {
    setCompanyToDeactivate(company)
    setOpenDropdown(null)
  }

  const handleActionMenuKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    const items = Array.from(actionMenuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [])
    if (items.length === 0) {
      return
    }

    const currentIndex = items.findIndex((item) => item === document.activeElement)

    switch (event.key) {
      case 'ArrowDown': {
        event.preventDefault()
        const nextIndex = currentIndex >= 0 ? (currentIndex + 1) % items.length : 0
        items[nextIndex]?.focus()
        break
      }
      case 'ArrowUp': {
        event.preventDefault()
        const nextIndex = currentIndex >= 0 ? (currentIndex - 1 + items.length) % items.length : items.length - 1
        items[nextIndex]?.focus()
        break
      }
      case 'Home':
        event.preventDefault()
        items[0]?.focus()
        break
      case 'End':
        event.preventDefault()
        items[items.length - 1]?.focus()
        break
      case 'Escape':
        event.preventDefault()
        setOpenDropdown(null)
        break
      default:
        break
    }
  }

  const getTypeBadgeColor = (type: CompanyType) => {
    switch (type) {
      case 'customer':
        return 'bg-blue-100 text-blue-700'
      case 'partner':
        return 'bg-purple-100 text-purple-700'
      case 'internal':
        return 'bg-emerald-100 text-emerald-700'
      default:
        return 'bg-slate-100 text-slate-700'
    }
  }

  if (!isAdmin) {
    return (
      <div className="surface-card animate-fade-in rounded-2xl p-6 text-amber-700 bg-amber-50">
        You don't have permission to view this page.
      </div>
    )
  }

  return (
    <div className="page-stack">
      <PageHeader
        title="Company Management"
        subtitle="Manage companies and their users"
        actions={
          <button
            onClick={() => setShowCreateForm(true)}
            className="btn-primary table-action-btn flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Company
          </button>
        }
      />

      {/* Filters */}
      <div className="admin-sticky-toolbar">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="body-copy inline-flex items-center gap-2">
            <span className="admin-summary-badge">
              {isLoading ? 'Loading...' : `${data?.total ?? 0} companies`}
            </span>
          </div>

          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 lg:items-center">
            <div className="relative min-w-[220px] sm:col-span-2 lg:col-span-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search companies..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value)
                  setPage(1)
                }}
                className="input-field pl-10"
                aria-label="Search companies by name"
              />
            </div>
            <select
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value)
                setPage(1)
              }}
              className="select-field min-w-[150px]"
              aria-label="Filter by company type"
            >
              <option value="">All Types</option>
              <option value="customer">Customer</option>
              <option value="partner">Partner</option>
              <option value="internal">Internal</option>
            </select>
            <select
              value={activeFilter}
              onChange={(e) => {
                setActiveFilter(e.target.value)
                setPage(1)
              }}
              className="select-field min-w-[150px]"
              aria-label="Filter by status"
            >
              <option value="">All Status</option>
              <option value="true">Active</option>
              <option value="false">Inactive</option>
            </select>
          </div>
        </div>
      </div>

      {/* Companies Table */}
      <div className="admin-table-shell">
        <div className="admin-table-scroll">
          <table className="admin-table">
            <thead className="admin-table-head">
              <tr>
                <th>Company</th>
                <th>Type</th>
                <th>Users</th>
                <th>Assigned Docs</th>
                <th>Status</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr className="admin-table-row">
                  <td colSpan={6} className="px-5 py-10 text-center body-copy">
                    Loading companies...
                  </td>
                </tr>
              ) : error ? (
                <tr className="admin-table-row">
                  <td colSpan={6} className="px-5 py-10 text-center text-sm text-rose-600">
                    Failed to load companies
                  </td>
                </tr>
              ) : data?.items.length === 0 ? (
                <tr className="admin-table-row">
                  <td colSpan={6} className="px-5 py-10 text-center body-copy">
                    No companies found
                  </td>
                </tr>
              ) : (
                data?.items.map((company) => (
                  <tr key={company.id} className="admin-table-row">
                    <td className="admin-table-cell">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center">
                          <Building2 className="w-5 h-5 text-blue-600" />
                        </div>
                        <div>
                          <div className="card-title">{company.name}</div>
                          <div className="helper-copy">{company.slug}</div>
                        </div>
                      </div>
                    </td>
                    <td className="admin-table-cell">
                      <span className={`pill capitalize ${getTypeBadgeColor(company.company_type)}`}>
                        {company.company_type}
                      </span>
                    </td>
                    <td className="admin-table-cell">
                      <Link to={`/admin/companies/${company.id}`} className="body-copy flex items-center gap-2 text-slate-600 hover:text-blue-700">
                        <Users className="w-4 h-4" />
                        {company.user_count}
                      </Link>
                    </td>
                    <td className="admin-table-cell">
                      <Link to={`/admin/companies/${company.id}`} className="body-copy flex items-center gap-2 text-slate-600 hover:text-blue-700">
                        <FileText className="w-4 h-4" />
                        {company.assigned_document_count}
                      </Link>
                    </td>
                    <td className="admin-table-cell">
                      <span className={`pill ${
                        company.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
                      }`}>
                        {company.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="admin-table-cell text-right">
                      <div className="relative inline-block">
                        <button
                          ref={(node) => {
                            actionTriggerRefs.current[company.id] = node
                          }}
                          type="button"
                          onClick={() => setOpenDropdown(openDropdown === company.id ? null : company.id)}
                          onKeyDown={(event) => {
                            if (event.key === 'ArrowDown') {
                              event.preventDefault()
                              setOpenDropdown(company.id)
                            }
                          }}
                          className="admin-icon-action"
                          aria-label={`Open actions for ${company.name}`}
                          aria-haspopup="menu"
                          aria-expanded={openDropdown === company.id}
                          aria-controls={`company-actions-${company.id}`}
                        >
                          <MoreVertical className="w-4 h-4 text-slate-500" />
                        </button>
                        {openDropdown === company.id && (
                          <div
                            ref={actionMenuRef}
                            id={`company-actions-${company.id}`}
                            role="menu"
                            tabIndex={-1}
                            aria-label={`${company.name} actions`}
                            className="dropdown-menu absolute right-0 mt-1 w-48 z-50"
                            onKeyDown={handleActionMenuKeyDown}
                          >
                            <Link
                              to={`/admin/companies/${company.id}`}
                              className="dropdown-item rounded-t-xl"
                              onClick={() => setOpenDropdown(null)}
                              role="menuitem"
                            >
                              <Eye className="w-4 h-4" />
                              View Details
                            </Link>
                            <button
                              type="button"
                              onClick={() => { setEditingCompany(company); setOpenDropdown(null) }}
                              className="dropdown-item w-full"
                              role="menuitem"
                            >
                              <Edit className="w-4 h-4" />
                              Edit
                            </button>
                            {company.is_active && (
                              <button
                                type="button"
                                onClick={() => handleDeleteCompany(company)}
                                className="dropdown-item w-full rounded-b-xl text-rose-600 hover:bg-rose-50 hover:text-rose-700"
                                role="menuitem"
                              >
                                <Trash2 className="w-4 h-4" />
                                Deactivate
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="surface-card flex justify-center gap-2 rounded-2xl px-4 py-3">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn-ghost table-action-btn disabled:opacity-50"
          >
            Previous
          </button>
          <span className="body-copy px-4 py-2">
            Page {page} of {data.total_pages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(data.total_pages, p + 1))}
            disabled={page === data.total_pages}
            className="btn-ghost table-action-btn disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}

      {/* Create/Edit Modal */}
      {(showCreateForm || editingCompany) && (
        <CompanyForm
          company={editingCompany}
          onClose={() => { setShowCreateForm(false); setEditingCompany(null) }}
          onSuccess={() => {
            setShowCreateForm(false)
            setEditingCompany(null)
            queryClient.invalidateQueries({ queryKey: ['companies'] })
          }}
        />
      )}

      {/* Click outside to close dropdown */}
      {openDropdown && (
        <button
          type="button"
          className="fixed inset-0 z-0"
          onClick={() => setOpenDropdown(null)}
          aria-label="Close company actions menu"
          tabIndex={-1}
        />
      )}

      {/* Deactivate confirmation */}
      <ConfirmationDialog
        open={!!companyToDeactivate}
        title="Deactivate company"
        description={`Are you sure you want to deactivate "${companyToDeactivate?.name}"? This will not delete any data.`}
        confirmLabel="Deactivate"
        isLoading={deleteCompanyMutation.isPending}
        onConfirm={() => {
          if (companyToDeactivate) {
            deleteCompanyMutation.mutate(companyToDeactivate.id, { onSettled: () => setCompanyToDeactivate(null) })
          }
        }}
        onCancel={() => setCompanyToDeactivate(null)}
      />
    </div>
  )
}
