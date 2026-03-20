import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import type { TimeSeriesPoint } from '@/types'
import { useChartTheme } from './useChartTheme'

interface LineChartWidgetProps {
  title: string
  data: TimeSeriesPoint[]
  color?: string
  height?: number
  loading?: boolean
  secondaryData?: TimeSeriesPoint[]
  secondaryColor?: string
  secondaryLabel?: string
  label?: string
}

export function LineChartWidget({
  title,
  data,
  color = '#3B82F6',
  height = 300,
  loading,
  secondaryData,
  secondaryColor = '#10B981',
  secondaryLabel,
  label,
}: LineChartWidgetProps) {
  const theme = useChartTheme()
  const primaryColor = color || theme.series[0]
  const secondarySeriesColor = secondaryColor || theme.series[1]

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

  // Merge datasets if we have secondary data
  const chartData = secondaryData
    ? data.map((point, i) => ({
        date: point.date,
        [label || 'value']: point.value,
        [secondaryLabel || 'secondary']: secondaryData[i]?.value || 0,
      }))
    : data

  return (
    <div
      role="img"
      aria-label={title}
      className="surface-card rounded-xl p-6 dark:border-slate-800 dark:bg-slate-900"
    >
      <h3 className="mb-4 text-lg font-medium text-slate-900 dark:text-slate-100">{title}</h3>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} />
          <XAxis 
            dataKey="date" 
            tick={{ fontSize: 12, fill: theme.axis }} 
            tickLine={false}
            axisLine={{ stroke: theme.grid }}
          />
          <YAxis 
            tick={{ fontSize: 12, fill: theme.axis }} 
            tickLine={false}
            axisLine={{ stroke: theme.grid }}
          />
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
          {secondaryData && <Legend wrapperStyle={{ color: theme.textMuted }} />}
          <Line
            type="monotone"
            dataKey={label || 'value'}
            stroke={primaryColor}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: primaryColor }}
          />
          {secondaryData && (
            <Line
              type="monotone"
              dataKey={secondaryLabel || 'secondary'}
              stroke={secondarySeriesColor}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: secondarySeriesColor }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
