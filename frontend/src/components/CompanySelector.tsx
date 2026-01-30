import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { X, Search, Building2, Check } from 'lucide-react'

interface CompanySelectorProps {
  selectedIds: number[]
  onChange: (ids: number[]) => void
  disabled?: boolean
}

export default function CompanySelector({ 
  selectedIds, 
  onChange, 
  disabled = false 
}: CompanySelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState('')
  
  const { data: companiesData } = useQuery({
    queryKey: ['companies-selector'],
    queryFn: () => api.getCompanies({ per_page: 100, is_active: true }),
  })
  
  const companies = companiesData?.items || []
  
  const selectedCompanies = companies.filter(c => selectedIds.includes(c.id))
  
  const filteredCompanies = companies.filter(c => 
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    c.slug.toLowerCase().includes(search.toLowerCase())
  )
  
  const toggleCompany = (companyId: number) => {
    if (selectedIds.includes(companyId)) {
      onChange(selectedIds.filter(id => id !== companyId))
    } else {
      onChange([...selectedIds, companyId])
    }
  }
  
  const removeCompany = (companyId: number) => {
    onChange(selectedIds.filter(id => id !== companyId))
  }
  
  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (!target.closest('.company-selector')) {
        setIsOpen(false)
      }
    }
    
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])
  
  return (
    <div className="company-selector relative">
      {/* Selected companies chips */}
      {selectedCompanies.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2">
          {selectedCompanies.map(company => (
            <span 
              key={company.id}
              className="inline-flex items-center gap-1 px-2 py-1 bg-primary-100 text-primary-700 rounded-full text-sm"
            >
              <Building2 className="w-3 h-3" />
              {company.name}
              {!disabled && (
                <button
                  type="button"
                  onClick={() => removeCompany(company.id)}
                  className="ml-1 hover:bg-primary-200 rounded-full p-0.5"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </span>
          ))}
        </div>
      )}
      
      {/* Dropdown trigger */}
      {!disabled && (
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="w-full px-3 py-2 border border-slate-300 rounded-xl text-left text-slate-600 hover:border-slate-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        >
          {selectedIds.length === 0 
            ? 'Select companies...' 
            : `${selectedIds.length} company(ies) selected`
          }
        </button>
      )}
      
      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-10 mt-1 w-full bg-white border border-slate-200 rounded-xl shadow-lg max-h-64 overflow-hidden">
          {/* Search */}
          <div className="p-2 border-b">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search companies..."
                className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>
          
          {/* Options */}
          <div className="max-h-48 overflow-y-auto">
            {filteredCompanies.length === 0 ? (
              <div className="px-4 py-3 text-slate-500 text-sm">
                No companies found
              </div>
            ) : (
              filteredCompanies.map(company => (
                <button
                  key={company.id}
                  type="button"
                  onClick={() => toggleCompany(company.id)}
                  className="w-full flex items-center gap-3 px-4 py-2 hover:bg-slate-50 text-left"
                >
                  <div className={`w-5 h-5 rounded border flex items-center justify-center ${
                    selectedIds.includes(company.id) 
                      ? 'bg-primary-600 border-primary-600' 
                      : 'border-slate-300'
                  }`}>
                    {selectedIds.includes(company.id) && (
                      <Check className="w-3 h-3 text-white" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="font-medium text-slate-900">{company.name}</div>
                    <div className="text-xs text-slate-500">{company.slug}</div>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    company.company_type === 'customer' ? 'bg-sky-100 text-sky-700' :
                    company.company_type === 'partner' ? 'bg-purple-100 text-purple-700' :
                    'bg-emerald-100 text-emerald-700'
                  }`}>
                    {company.company_type}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
