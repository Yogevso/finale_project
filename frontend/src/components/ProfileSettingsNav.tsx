import { ShieldCheck, User, MonitorSmartphone } from 'lucide-react'
import { NavLink } from 'react-router-dom'

const profileNavItems = [
  {
    path: '/profile',
    label: 'Profile',
    icon: User,
  },
  {
    path: '/profile/sessions',
    label: 'Sessions',
    icon: MonitorSmartphone,
  },
  {
    path: '/profile/security-events',
    label: 'Security Events',
    icon: ShieldCheck,
  },
] as const

export default function ProfileSettingsNav() {
  return (
    <nav className="surface-card rounded-2xl p-2 flex flex-wrap gap-2" aria-label="Profile settings sections">
      {profileNavItems.map((item) => {
        const Icon = item.icon
        return (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/profile'}
            className={({ isActive }) =>
              `inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm transition-colors ${
                isActive
                  ? 'bg-sky-100 text-sky-800 border border-sky-200 font-medium'
                  : 'text-slate-600 hover:bg-slate-100'
              }`
            }
          >
            <Icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        )
      })}
    </nav>
  )
}
