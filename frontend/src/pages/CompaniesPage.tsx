import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/lib/auth'
import { api } from '@/lib/api'
import { Building2, Search, Plus, Users, FileText, MoreVertical, Eye, Trash2, Edit } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { Company, CompanyType } from '@/types'
import CompanyForm from '@/components/CompanyForm'

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

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
  }

  const handleDeleteCompany = async (company: Company) => {
    if (confirm(`Are you sure you want to deactivate "${company.name}"? This will not delete any data.`)) {
      await deleteCompanyMutation.mutateAsync(company.id)
    }
    setOpenDropdown(null)
  }

  const getTypeBadgeColor = (type: CompanyType) => {
    switch (type) {
      case 'customer':
        return 'bg-sky-100 text-sky-700'
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
      <div className="surface-card rounded-2xl p-6 text-amber-700 bg-amber-50">
        You don't have permission to view this page.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-display font-bold text-slate-900">Company Management</h1>
          <p className="text-slate-500 mt-1">Manage companies and their users</p>
        </div>
        <button
          onClick={() => setShowCreateForm(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Add Company
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search companies..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input-field pl-10"
            />
          </div>
          <button type="submit" className="px-4 py-2 bg-slate-100 rounded-xl hover:bg-slate-200">
            Search
          </button>
        </form>
        <select
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); setPage(1) }}
          className="select-field"
        >
          <option value="">All Types</option>
          <option value="customer">Customer</option>
          <option value="partner">Partner</option>
          <option value="internal">Internal</option>
        </select>
        <select
          value={activeFilter}
          onChange={(e) => { setActiveFilter(e.target.value); setPage(1) }}
          className="select-field"
        >
          <option value="">All Status</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
      </div>

      {/* Companies Table */}
      <div className="surface-card rounded-2xl overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Company</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Users</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Documents</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Status</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {isLoading ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                  Loading companies...
                </td>
              </tr>
            ) : error ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-rose-500">
                  Failed to load companies
                </td>
              </tr>
            ) : data?.items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                  No companies found
                </td>
              </tr>
            ) : (
              data?.items.map((company) => (
                <tr key={company.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-sky-100 rounded-xl flex items-center justify-center">
                        <Building2 className="w-5 h-5 text-sky-600" />
                      </div>
                      <div>
                        <div className="font-medium text-slate-900">{company.name}</div>
                        <div className="text-sm text-slate-500">{company.slug}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`pill ${getTypeBadgeColor(company.company_type)}`}>
                      {company.company_type}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2 text-slate-600">
                      <Users className="w-4 h-4" />
                      {company.user_count}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2 text-slate-600">
                      <FileText className="w-4 h-4" />
                      {company.document_count}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`pill ${
                      company.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
                    }`}>
                      {company.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="relative inline-block">
                      <button
                        onClick={() => setOpenDropdown(openDropdown === company.id ? null : company.id)}
                        className="p-2 hover:bg-slate-100 rounded-xl"
                      >
                        <MoreVertical className="w-4 h-4 text-slate-500" />
                      </button>
                      {openDropdown === company.id && (
                        <div className="absolute right-0 mt-1 w-48 bg-white border border-slate-200 rounded-xl shadow-lg z-10">
                          <Link
                            to={`/admin/companies/${company.id}`}
                            className="flex items-center gap-2 px-4 py-2 text-slate-700 hover:bg-slate-50 rounded-t-xl"
                            onClick={() => setOpenDropdown(null)}
                          >
                            <Eye className="w-4 h-4" />
                            View Details
                          </Link>
                          <button
                            onClick={() => { setEditingCompany(company); setOpenDropdown(null) }}
                            className="flex items-center gap-2 px-4 py-2 text-slate-700 hover:bg-slate-50 w-full text-left"
                          >
                            <Edit className="w-4 h-4" />
                            Edit
                          </button>
                          {company.is_active && (
                            <button
                              onClick={() => handleDeleteCompany(company)}
                              className="flex items-center gap-2 px-4 py-2 text-rose-600 hover:bg-rose-50 w-full text-left rounded-b-xl"
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

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn-ghost disabled:opacity-50"
          >
            Previous
          </button>
          <span className="px-4 py-2 text-slate-600">
            Page {page} of {data.pages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(data.pages, p + 1))}
            disabled={page === data.pages}
            className="btn-ghost disabled:opacity-50"
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
        <div
          className="fixed inset-0 z-0"
          onClick={() => setOpenDropdown(null)}
        />
      )}
    </div>
  )
}
