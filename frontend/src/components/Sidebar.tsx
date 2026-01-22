import { NavLink } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { getNavigationForRole, getSectionLabel, type RouteConfig } from '@/config/routes'

export default function Sidebar() {
  const { user } = useAuth()
  
  const navItems = getNavigationForRole(user?.role || null)
  
  // Group items by section
  const groupedItems = navItems.reduce((acc, item) => {
    const section = item.section || 'main'
    if (!acc[section]) acc[section] = []
    acc[section].push(item)
    return acc
  }, {} as Record<string, RouteConfig[]>)

  const sections: RouteConfig['section'][] = ['main', 'management', 'admin']

  return (
    <aside className="fixed left-0 top-16 bottom-0 w-64 bg-white border-r border-gray-200 overflow-y-auto">
      <nav className="p-4 space-y-6">
        {sections.map((section) => {
          const items = groupedItems[section || 'main']
          if (!items || items.length === 0) return null
          
          return (
            <div key={section}>
              {section && section !== 'main' && (
                <h3 className="px-4 mb-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  {getSectionLabel(section)}
                </h3>
              )}
              <div className="space-y-1">
                {items.map((item) => (
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
              </div>
            </div>
          )
        })}
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
