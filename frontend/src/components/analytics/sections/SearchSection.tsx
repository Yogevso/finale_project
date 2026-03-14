import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, BarChart3, MousePointerClick, Search } from 'lucide-react'

import { api } from '@/lib/api'

export function SearchSection() {
  const [days, setDays] = useState(30)

  const { data, isLoading } = useQuery({
    queryKey: ['search-analytics', days],
    queryFn: () => api.getSearchAnalytics(days),
  })

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Period selector */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-slate-500">Period:</span>
        {[7, 30, 90].map((d) => (
          <button
            key={d}
            onClick={() => setDays(d)}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              days === d ? 'bg-sky-100 text-sky-700 font-medium' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            {d}d
          </button>
        ))}
      </div>

      {/* Stats summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="surface-card rounded-2xl p-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sky-100 flex items-center justify-center">
              <Search className="h-5 w-5 text-sky-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900">{data?.total_searches ?? 0}</p>
              <p className="text-sm text-slate-500">Total Searches</p>
            </div>
          </div>
        </div>
        <div className="surface-card rounded-2xl p-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center">
              <MousePointerClick className="h-5 w-5 text-emerald-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900">{data?.total_clicks ?? 0}</p>
              <p className="text-sm text-slate-500">Result Clicks</p>
            </div>
          </div>
        </div>
        <div className="surface-card rounded-2xl p-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center">
              <BarChart3 className="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900">{data?.click_through_rate ?? 0}%</p>
              <p className="text-sm text-slate-500">Click-Through Rate</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top queries */}
        <div className="surface-card rounded-2xl">
          <div className="px-6 py-4 border-b border-slate-200">
            <h3 className="font-display font-semibold text-slate-900 flex items-center gap-2">
              <Search className="h-4 w-4" />
              Top Queries
            </h3>
          </div>
          <div className="p-4">
            {data?.top_queries?.length === 0 ? (
              <p className="text-sm text-slate-500 py-4 text-center">No search data yet</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-500 border-b border-slate-100">
                    <th className="pb-2">Query</th>
                    <th className="pb-2 text-right">Count</th>
                    <th className="pb-2 text-right">Avg Results</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.top_queries?.map((q, i) => (
                    <tr key={i} className="border-b border-slate-50">
                      <td className="py-2 text-slate-900 font-medium truncate max-w-[200px]">{q.query}</td>
                      <td className="py-2 text-right text-slate-600">{q.count}</td>
                      <td className="py-2 text-right text-slate-600">{q.avg_results}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Zero-result queries */}
        <div className="surface-card rounded-2xl">
          <div className="px-6 py-4 border-b border-slate-200">
            <h3 className="font-display font-semibold text-slate-900 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              Zero-Result Queries
            </h3>
            <p className="text-xs text-slate-500 mt-1">Queries that returned no results — consider adding content</p>
          </div>
          <div className="p-4">
            {data?.zero_result_queries?.length === 0 ? (
              <p className="text-sm text-slate-500 py-4 text-center">No zero-result queries</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-500 border-b border-slate-100">
                    <th className="pb-2">Query</th>
                    <th className="pb-2 text-right">Count</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.zero_result_queries?.map((q, i) => (
                    <tr key={i} className="border-b border-slate-50">
                      <td className="py-2 text-slate-900 font-medium truncate max-w-[200px]">{q.query}</td>
                      <td className="py-2 text-right text-slate-600">{q.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
