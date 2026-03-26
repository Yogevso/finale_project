import Skeleton from '@/components/Skeleton'
import { SearchInput } from '@/components/form'
import type { Company, UserRole } from '@/types'

interface UsersFiltersToolbarProps {
  isLoading: boolean
  totalUsers: number
  pendingInvitationCount: number
  searchInput: string
  onSearchInputChange: (value: string) => void
  onSearchClear: () => void
  roleFilter: UserRole | ''
  onRoleFilterChange: (value: UserRole | '') => void
  companyFilter: number | ''
  onCompanyFilterChange: (value: number | '') => void
  statusFilter: boolean | ''
  onStatusFilterChange: (value: boolean | '') => void
  roles: UserRole[]
  companies: Company[]
}

export function UsersFiltersToolbar({
  isLoading,
  totalUsers,
  pendingInvitationCount,
  searchInput,
  onSearchInputChange,
  onSearchClear,
  roleFilter,
  onRoleFilterChange,
  companyFilter,
  onCompanyFilterChange,
  statusFilter,
  onStatusFilterChange,
  roles,
  companies,
}: UsersFiltersToolbarProps) {
  return (
    <div className="admin-sticky-toolbar">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="body-copy inline-flex flex-wrap items-center gap-2">
          <span className="admin-summary-badge">
            {isLoading ? <Skeleton className="h-4 w-20" /> : `${totalUsers} users`}
          </span>
          {pendingInvitationCount > 0 ? (
            <span className="pill border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/70 dark:bg-amber-950/30 dark:text-amber-200">
              {pendingInvitationCount} pending invites
            </span>
          ) : null}
        </div>

        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4 xl:items-center">
          <div className="min-w-[220px] sm:col-span-2 xl:col-span-1">
            <SearchInput
              value={searchInput}
              onChange={(event) => onSearchInputChange(event.target.value)}
              onClear={onSearchClear}
              placeholder="Search users..."
              aria-label="Search users by name or email"
            />
          </div>

          <select
            value={roleFilter}
            onChange={(event) => onRoleFilterChange(event.target.value as UserRole | '')}
            className="select-field min-w-[150px]"
          >
            <option value="">All Roles</option>
            {roles.map((role) => (
              <option key={role} value={role}>
                {role.replace('_', ' ')}
              </option>
            ))}
          </select>

          <select
            value={companyFilter}
            onChange={(event) =>
              onCompanyFilterChange(event.target.value ? Number(event.target.value) : '')
            }
            className="select-field min-w-[150px]"
          >
            <option value="">All Companies</option>
            {companies.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name}
              </option>
            ))}
          </select>

          <select
            value={statusFilter === '' ? '' : statusFilter ? 'active' : 'inactive'}
            onChange={(event) => {
              if (event.target.value === '') {
                onStatusFilterChange('')
                return
              }
              onStatusFilterChange(event.target.value === 'active')
            }}
            className="select-field min-w-[150px]"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
      </div>
    </div>
  )
}
