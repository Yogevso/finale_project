import type { UserRole } from '@/types'

export const ALL_USER_ROLES: UserRole[] = [
  'system_admin',
  'admin',
  'manager',
  'editor',
  'viewer',
  'customer',
]

export function getRoleBadgeColor(role: UserRole | string) {
  switch (role) {
    case 'system_admin':
      return 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-200'
    case 'admin':
      return 'bg-purple-100 text-purple-700 dark:bg-purple-950/40 dark:text-purple-200'
    case 'manager':
      return 'bg-amber-100 text-amber-700 dark:bg-amber-950/30 dark:text-amber-200'
    case 'editor':
      return 'bg-sky-100 text-sky-700 dark:bg-sky-950/40 dark:text-sky-200'
    case 'customer':
      return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200'
    default:
      return 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
  }
}
