import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'

interface DonutChartData {
  name: string
  value: number
}

interface DonutChartWidgetProps {
  title: string
  data: DonutChartData[]
  height?: number
  loading?: boolean
  centerLabel?: string
  centerValue?: string | number
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16']

export function DonutChartWidget({
  title,
  data,
  height = 300,
  loading,
  centerLabel,
  centerValue,
}: DonutChartWidgetProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="h-5 bg-gray-200 rounded w-40 mb-4 animate-pulse"></div>
        <div className="animate-pulse" style={{ height }}>
          <div className="bg-gray-100 rounded-full w-48 h-48 mx-auto"></div>
        </div>
      </div>
    )
  }

  const filteredData = data.filter((d) => d.value > 0)

  if (filteredData.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">{title}</h3>
        <div className="flex items-center justify-center" style={{ height }}>
          <p className="text-gray-500">No data available</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">{title}</h3>
      <div className="relative">
        <ResponsiveContainer width="100%" height={height}>
          <PieChart>
            <Pie
              data={filteredData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={80}
              paddingAngle={2}
              dataKey="value"
            >
              {filteredData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #E5E7EB',
                borderRadius: '8px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
              }}
              formatter={(value) => [value, '']}
            />
            <Legend
              layout="horizontal"
              verticalAlign="bottom"
              align="center"
              formatter={(value) => <span className="text-sm text-gray-600">{value}</span>}
            />
          </PieChart>
        </ResponsiveContainer>
        {centerLabel && centerValue !== undefined && (
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center" style={{ marginTop: '-20px' }}>
            <p className="text-2xl font-bold text-gray-900">{centerValue}</p>
            <p className="text-xs text-gray-500">{centerLabel}</p>
          </div>
        )}
      </div>
    </div>
  )
}
