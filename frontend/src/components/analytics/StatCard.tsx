import { LucideIcon } from 'lucide-react'

interface StatCardProps {
  title: string
  value: number | string
  icon: LucideIcon
  trend?: { value: number; isPositive: boolean }
  subtitle?: string
  loading?: boolean
}

export function StatCard({ title, value, icon: Icon, trend, subtitle, loading }: StatCardProps) {
  if (loading) {
    return (
      <div className="surface-card rounded-xl p-6 animate-pulse dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <div className="h-4 w-24 rounded bg-slate-200 dark:bg-slate-700"></div>
            <div className="h-8 w-16 rounded bg-slate-200 dark:bg-slate-700"></div>
          </div>
          <div className="rounded-full bg-slate-100 p-3 dark:bg-slate-800">
            <div className="h-6 w-6 rounded bg-slate-200 dark:bg-slate-700"></div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="surface-card rounded-xl p-6 transition-shadow hover:shadow-md dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{title}</p>
          <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">{value}</p>
          {subtitle ? (
            <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">{subtitle}</p>
          ) : null}
        </div>
        <div className="rounded-full bg-sky-50 p-3 dark:bg-sky-950/40">
          <Icon className="h-6 w-6 text-sky-600 dark:text-sky-300" />
        </div>
      </div>
      {trend ? (
        <div
          className={`mt-3 flex items-center text-sm ${
            trend.isPositive
              ? 'text-emerald-600 dark:text-emerald-400'
              : 'text-rose-600 dark:text-rose-400'
          }`}
        >
          <span className="mr-1">{trend.isPositive ? '↑' : '↓'}</span>
          <span>{Math.abs(trend.value)}% vs previous period</span>
        </div>
      ) : null}
    </div>
  )
}
