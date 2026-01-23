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
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="h-5 bg-gray-200 rounded w-40 mb-4 animate-pulse"></div>
        <div className="animate-pulse" style={{ height }}>
          <div className="bg-gray-100 rounded h-full"></div>
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
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis 
            dataKey="date" 
            tick={{ fontSize: 12 }} 
            tickLine={false}
            axisLine={{ stroke: '#E5E7EB' }}
          />
          <YAxis 
            tick={{ fontSize: 12 }} 
            tickLine={false}
            axisLine={{ stroke: '#E5E7EB' }}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: 'white', 
              border: '1px solid #E5E7EB',
              borderRadius: '8px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}
          />
          {secondaryData && <Legend />}
          <Line
            type="monotone"
            dataKey={label || 'value'}
            stroke={color}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
          {secondaryData && (
            <Line
              type="monotone"
              dataKey={secondaryLabel || 'secondary'}
              stroke={secondaryColor}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
