import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { getNavigationForRole } from '@/config/routes'
import NotificationBell from './NotificationBell'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const navItems = getNavigationForRole(user?.role || null)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Zip B Style Header */}
      <header className="sticky top-0 z-20 backdrop-blur bg-white/80 border-b border-slate-200">
        <div className="container mx-auto px-4 py-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          {/* Logo */}
          <div className="flex items-center gap-4">
            <NavLink to="/dashboard" className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-2xl bg-slate-900 text-white flex items-center justify-center font-semibold font-display">
                DP
              </div>
              <div>
                <div className="text-sm text-slate-500">Management</div>
                <div className="text-lg font-semibold text-slate-900 leading-tight font-display">Document Portal</div>
              </div>
            </NavLink>
          </div>

          {/* Navigation */}
          <nav className="flex flex-wrap items-center gap-1 text-sm" aria-label="Primary">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `px-4 py-2 rounded-full transition-colors ${
                    isActive
                      ? 'bg-sky-100 text-sky-800 font-medium'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }`
                }
              >
                <span className="mr-1.5">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </nav>

          {/* User Info & Actions */}
          <div className="flex items-center gap-3 text-sm">
            <div className="hidden md:flex items-center gap-2">
              <span className="text-slate-500">{user?.full_name}</span>
              <span className="pill capitalize">{user?.role}</span>
            </div>
            
            <NotificationBell />
            
            <button
              onClick={handleLogout}
              className="btn-ghost"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1">
        <div className="container mx-auto px-4 py-8">
          <Outlet />
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white/80 backdrop-blur">
        <div className="container mx-auto px-4 py-6 text-center text-sm text-slate-500">
          <p>Document Portal V2</p>
          <p className="text-xs mt-1">Built with React + FastAPI</p>
        </div>
      </footer>
    </div>
  )
}
