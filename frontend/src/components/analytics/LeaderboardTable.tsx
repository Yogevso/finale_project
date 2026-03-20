import OptimizedImage from '@/components/OptimizedImage'

interface LeaderboardItem {
  rank: number
  name: string
  value: number | string
  subValue?: string
  imageUrl?: string
}

interface LeaderboardTableProps {
  title: string
  items: LeaderboardItem[]
  valueLabel?: string
  loading?: boolean
}

export function LeaderboardTable({
  title,
  items,
  valueLabel = 'Value',
  loading,
}: LeaderboardTableProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow p-6">
        <div className="h-5 bg-slate-200 rounded w-40 mb-4 animate-pulse"></div>
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex items-center gap-4 animate-pulse">
              <div className="w-8 h-8 bg-slate-200 rounded-full"></div>
              <div className="flex-1 h-4 bg-slate-200 rounded"></div>
              <div className="w-16 h-4 bg-slate-200 rounded"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow p-6">
        <h3 className="text-lg font-medium text-slate-900 mb-4">{title}</h3>
        <div className="flex items-center justify-center py-8">
          <p className="text-slate-500">No data available</p>
        </div>
      </div>
    )
  }

  const getRankBadge = (rank: number) => {
    if (rank === 1) return 'bg-amber-100 text-amber-800'
    if (rank === 2) return 'bg-slate-100 text-slate-800'
    if (rank === 3) return 'bg-orange-100 text-orange-800'
    return 'bg-sky-50 text-sky-700'
  }

  return (
    <div className="bg-white rounded-xl shadow p-6">
      <h3 className="text-lg font-medium text-slate-900 mb-4">{title}</h3>
      <div className="overflow-hidden">
        <table className="min-w-full">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left text-xs font-medium text-slate-500 uppercase tracking-wider pb-3 w-12">
                Rank
              </th>
              <th className="text-left text-xs font-medium text-slate-500 uppercase tracking-wider pb-3">
                Name
              </th>
              <th className="text-right text-xs font-medium text-slate-500 uppercase tracking-wider pb-3">
                {valueLabel}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {items.map((item) => (
              <tr key={item.rank} className="hover:bg-slate-50">
                <td className="py-3">
                  <span
                    className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-sm font-medium ${getRankBadge(
                      item.rank
                    )}`}
                  >
                    {item.rank}
                  </span>
                </td>
                <td className="py-3">
                  <div className="flex items-center gap-3">
                    {item.imageUrl && (
                      <OptimizedImage
                        src={item.imageUrl}
                        alt=""
                        className="w-8 h-8 rounded-full object-cover"
                        height={32}
                        sizes="32px"
                        width={32}
                      />
                    )}
                    <div>
                      <p className="text-sm font-medium text-slate-900">{item.name}</p>
                      {item.subValue && (
                        <p className="text-xs text-slate-500">{item.subValue}</p>
                      )}
                    </div>
                  </div>
                </td>
                <td className="py-3 text-right">
                  <span className="text-sm font-semibold text-slate-900">{item.value}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
