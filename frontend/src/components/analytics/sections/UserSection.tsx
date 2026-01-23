import { Users, UserCheck, Activity } from 'lucide-react'
import { StatCard } from '../StatCard'
import { BarChartWidget } from '../BarChartWidget'
import { LeaderboardTable } from '../LeaderboardTable'
import { LineChartWidget } from '../LineChartWidget'
import { useUserAnalytics } from '../hooks/useAnalytics'
import type { AnalyticsQueryParams, UserActivityItem } from '@/types'

interface UserSectionProps {
  params?: AnalyticsQueryParams
}

export function UserSection({ params }: UserSectionProps) {
  const { data: userAnalytics, isLoading } = useUserAnalytics(params)

  const usersByRole = userAnalytics
    ? Object.entries(userAnalytics.users_by_role).map(([role, count]) => ({
        name: role.replace('_', ' ').toUpperCase(),
        value: count as number,
      }))
    : []

  const mostActiveUsers = userAnalytics?.most_active_users.map((user: UserActivityItem, idx: number) => ({
    rank: idx + 1,
    name: user.full_name || user.username,
    value: user.action_count,
    subValue: user.role,
  })) || []

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-gray-900">User Analytics</h2>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Users"
          value={userAnalytics?.total_users || 0}
          icon={Users}
          loading={isLoading}
        />
        <StatCard
          title="Active Users"
          value={userAnalytics?.active_users || 0}
          icon={UserCheck}
          loading={isLoading}
          subtitle="Active in period"
        />
        <StatCard
          title="Inactive Users"
          value={userAnalytics?.inactive_users || 0}
          icon={Users}
          loading={isLoading}
        />
        <StatCard
          title="Activity Rate"
          value={`${Math.round(((userAnalytics?.active_users || 0) / (userAnalytics?.total_users || 1)) * 100)}%`}
          icon={Activity}
          loading={isLoading}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <BarChartWidget
          title="Users by Role"
          data={usersByRole}
          loading={isLoading}
          horizontal
          height={250}
        />
        <LineChartWidget
          title="New Users Over Time"
          data={userAnalytics?.new_users_over_time || []}
          loading={isLoading}
          color="#8B5CF6"
        />
      </div>

      {/* Most Active Users */}
      <LeaderboardTable
        title="Most Active Users"
        items={mostActiveUsers}
        valueLabel="Actions"
        loading={isLoading}
      />
    </div>
  )
}
