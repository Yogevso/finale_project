import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'
import { useChartTheme } from './useChartTheme'

interface PieChartData {
  name: string
  value: number
}

interface PieChartWidgetProps {
  title: string
  data: PieChartData[]
  height?: number
  loading?: boolean
}

export function PieChartWidget({
  title,
  data,
  height = 300,
  loading,
}: PieChartWidgetProps) {
  const theme = useChartTheme()
  const seriesColors = theme.series

  if (loading) {
    return (
      <div className="surface-card rounded-xl p-6 dark:border-slate-800 dark:bg-slate-900">
        <div className="mb-4 h-5 w-40 animate-pulse rounded bg-slate-200 dark:bg-slate-700"></div>
        <div className="animate-pulse" style={{ height }}>
          <div className="mx-auto h-48 w-48 rounded-full" style={{ backgroundColor: theme.surfaceMuted }}></div>
        </div>
      </div>
    )
  }

  const filteredData = data.filter((d) => d.value > 0)

  if (filteredData.length === 0) {
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
        <PieChart>
          <Pie
            data={filteredData}
            cx="50%"
            cy="50%"
            outerRadius={80}
            dataKey="value"
            label={({ name, percent, x, y, textAnchor }) => (
              <text
                x={x}
                y={y}
                fill={theme.textMuted}
                fontSize={12}
                textAnchor={textAnchor}
                dominantBaseline="central"
              >
                {`${name} ${((percent || 0) * 100).toFixed(0)}%`}
              </text>
            )}
            labelLine={false}
          >
            {filteredData.map((_, index) => (
              <Cell key={`cell-${index}`} fill={seriesColors[index % seriesColors.length]} />
            ))}
          </Pie>
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
            formatter={(value) => [value, '']}
          />
          <Legend
            layout="horizontal"
            verticalAlign="bottom"
            align="center"
            formatter={(value) => <span style={{ color: theme.textMuted }}>{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
