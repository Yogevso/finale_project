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
      <div className="bg-white rounded-xl shadow p-6 animate-pulse">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <div className="h-4 bg-slate-200 rounded w-24"></div>
            <div className="h-8 bg-slate-200 rounded w-16"></div>
          </div>
          <div className="p-3 bg-slate-100 rounded-full">
            <div className="w-6 h-6 bg-slate-200 rounded"></div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <p className="text-2xl font-bold text-slate-900">{value}</p>
          {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
        </div>
        <div className="p-3 bg-sky-50 rounded-full">
          <Icon className="w-6 h-6 text-sky-600" />
        </div>
      </div>
      {trend && (
        <div className={`mt-3 text-sm flex items-center ${trend.isPositive ? 'text-emerald-600' : 'text-rose-600'}`}>
          <span className="mr-1">{trend.isPositive ? '↑' : '↓'}</span>
          <span>{Math.abs(trend.value)}% vs previous period</span>
        </div>
      )}
    </div>
  )
}
