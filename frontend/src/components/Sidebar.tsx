import { NavLink } from 'react-router-dom'
import { useAuth } from '@/lib/auth'

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: '📊' },
  { path: '/documents', label: 'Documents', icon: '📄' },
  { path: '/users', label: 'Users', icon: '👥', adminOnly: true },
]

export default function Sidebar() {
  const { isAdmin } = useAuth()

  const filteredItems = navItems.filter((item) => !item.adminOnly || isAdmin)

  return (
    <aside className="fixed left-0 top-16 bottom-0 w-64 bg-white border-r border-gray-200 overflow-y-auto">
      <nav className="p-4 space-y-1">
        {filteredItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-700 font-medium'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`
            }
          >
            <span className="text-lg">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200">
        <div className="text-xs text-gray-400 text-center">
          Document Portal V2
          <br />
          Built with React + FastAPI
        </div>
      </div>
    </aside>
  )
}
