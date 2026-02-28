import { BarChart3 } from 'lucide-react'

export function AnalyticsAccessDenied() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <BarChart3 className="w-16 h-16 text-slate-400 mx-auto mb-4" />
        <h2 className="text-xl font-display font-semibold text-slate-900 mb-2">Access Restricted</h2>
        <p className="text-slate-500">You need Manager or higher role to access analytics.</p>
      </div>
    </div>
  )
}

