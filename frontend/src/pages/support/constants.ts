const STATUS_COLORS: Record<string, string> = {
  open: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950/30 dark:text-yellow-200',
  in_progress: 'bg-blue-100 text-blue-800 dark:bg-blue-950/40 dark:text-blue-200',
  resolved: 'bg-green-100 text-green-800 dark:bg-green-950/30 dark:text-green-200',
  closed: 'bg-gray-100 text-gray-700 dark:bg-slate-800 dark:text-slate-300',
}

const PRIORITY_BADGE: Record<string, string> = {
  low: 'bg-gray-100 text-gray-600 dark:bg-slate-800 dark:text-slate-300',
  normal: 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-200',
  high: 'bg-orange-50 text-orange-700 dark:bg-orange-950/30 dark:text-orange-200',
  urgent: 'bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-200',
}

export function getSupportStatusColor(status: string) {
  return STATUS_COLORS[status] ?? STATUS_COLORS.open
}

export function getSupportPriorityBadge(priority: string) {
  return PRIORITY_BADGE[priority] ?? PRIORITY_BADGE.normal
}

export function formatSupportFileSize(bytes: number | null | undefined): string {
  if (!bytes || bytes < 1024) {
    return `${bytes ?? 0} B`
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
