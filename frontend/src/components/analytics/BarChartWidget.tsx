import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { useChartTheme } from './useChartTheme'

interface BarChartData {
  name: string
  value: number
}

interface BarChartWidgetProps {
  title: string
  data: BarChartData[]
  color?: string
  height?: number
  loading?: boolean
  horizontal?: boolean
}

export function BarChartWidget({
  title,
  data,
  color,
  height = 300,
  loading,
  horizontal = false,
}: BarChartWidgetProps) {
  const theme = useChartTheme()
  const seriesColors = theme.series

  if (loading) {
    return (
      <div className="surface-card rounded-xl p-6 dark:border-slate-800 dark:bg-slate-900">
        <div className="mb-4 h-5 w-40 animate-pulse rounded bg-slate-200 dark:bg-slate-700"></div>
        <div className="animate-pulse" style={{ height }}>
          <div className="h-full rounded" style={{ backgroundColor: theme.surfaceMuted }}></div>
        </div>
      </div>
    )
  }

  if (data.length === 0) {
    return (
      <div
        role="img"
        aria-label={title}
        className="surface-card rounded-xl p-6 dark:border-slate-800 dark:bg-slate-900"
      >
        <h3 className="mb-4 text-lg font-medium text-slate-900 dark:text-slate-100">{title}</h3>
        <div className="flex items-center justify-center" style={{ height }}>
          <p className="text-slate-500 dark:text-slate-400">No data available</p>
        </div>
      </div>
    )
  }

  return (
    <div
      role="img"
      aria-label={title}
      className="surface-card rounded-xl p-6 dark:border-slate-800 dark:bg-slate-900"
    >
      <h3 className="mb-4 text-lg font-medium text-slate-900 dark:text-slate-100">{title}</h3>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={data}
          layout={horizontal ? 'vertical' : 'horizontal'}
          margin={{ top: 5, right: 30, left: horizontal ? 80 : 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} />
          {horizontal ? (
            <>
              <XAxis type="number" tick={{ fontSize: 12, fill: theme.axis }} axisLine={{ stroke: theme.grid }} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 12, fill: theme.axis }} axisLine={{ stroke: theme.grid }} tickLine={false} width={70} />
            </>
          ) : (
            <>
              <XAxis dataKey="name" tick={{ fontSize: 12, fill: theme.axis }} axisLine={{ stroke: theme.grid }} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: theme.axis }} axisLine={{ stroke: theme.grid }} tickLine={false} />
            </>
          )}
          <Tooltip
            contentStyle={{
              backgroundColor: theme.tooltipBackground,
              border: `1px solid ${theme.tooltipBorder}`,
              borderRadius: '8px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
              color: theme.text,
            }}
            labelStyle={{ color: theme.text }}
            itemStyle={{ color: theme.text }}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={color || seriesColors[index % seriesColors.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
