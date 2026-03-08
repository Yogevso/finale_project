import { useEffect, useState } from 'react'
import { Menu, X } from 'lucide-react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { getNavigationForRole } from '@/config/routes'
import { useAuth } from '@/lib/auth'

import NotificationBell from './NotificationBell'

export default function Layout() {
  const { user, logout, isSystemAdmin } = useAuth()
  const navigate = useNavigate()
  const navItems = getNavigationForRole(user?.role || null)
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const isFullscreen = location.search.includes('fullscreen=1') || location.pathname.endsWith('/fullscreen')

  useEffect(() => {
    setMobileMenuOpen(false)
  }, [location.pathname, location.search])

  const handleLogout = () => {
    logout()
    navigate('/docs')
  }

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-slate-50 to-sky-50">
      {/* Intel-like Header */}
      {!isFullscreen && (
      <header className="sticky top-0 z-20 backdrop-blur bg-sky-100/85 border-b border-sky-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          {/* Logo + Mobile toggle */}
          <div className="flex items-center justify-between gap-3">
            <NavLink to="/dashboard" className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-2xl bg-slate-900 text-white flex items-center justify-center font-semibold font-display">
                DP
              </div>
              <div>
                <div className="text-xs uppercase tracking-widest text-slate-500">Internal Portal</div>
                <div className="text-lg font-semibold text-slate-900 leading-tight font-display">Developer Portal</div>
              </div>
            </NavLink>

            <div className="flex items-center gap-2 md:hidden">
              <NotificationBell />
              <button
                className="p-2 rounded-lg hover:bg-slate-100"
                onClick={() => setMobileMenuOpen((previous) => !previous)}
                aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              >
                {mobileMenuOpen ? (
                  <X className="h-5 w-5 text-slate-600" />
                ) : (
                  <Menu className="h-5 w-5 text-slate-600" />
                )}
              </button>
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1 text-sm" aria-label="Primary">
            {navItems.map((item) => {
              const Icon = item.icon
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `px-4 py-2 rounded-full transition-colors ${
                      isActive
                        ? 'bg-white text-sky-800 font-semibold border border-sky-200'
                        : 'text-slate-600 hover:bg-white/80 hover:text-slate-900'
                    }`
                  }
                >
                  <span className="mr-1.5 inline-flex align-middle">
                    <Icon className="h-4 w-4" />
                  </span>
                  {item.label}
                </NavLink>
              )
            })}
          </nav>

          {/* Desktop User Info & Actions */}
          <div className="hidden md:flex items-center gap-3 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-slate-500">{user?.full_name}</span>
              <span className="pill capitalize bg-white border-sky-200">{user?.role}</span>
            </div>

            {isSystemAdmin && (
              <NavLink to="/docs" className="btn-secondary text-xs">
                Viewer Portal
              </NavLink>
            )}

            <NotificationBell />

            <button onClick={handleLogout} className="btn-ghost">
              Sign Out
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-sky-200 bg-sky-50/90">
            <div className="max-w-7xl mx-auto px-4 py-4 space-y-2">
              {navItems.map((item) => {
                const Icon = item.icon
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) =>
                      `flex items-center px-4 py-2 rounded-xl transition-colors ${
                        isActive
                          ? 'bg-white text-sky-800 font-semibold'
                          : 'text-slate-600 hover:bg-white'
                      }`
                    }
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    <span className="mr-2 inline-flex align-middle">
                      <Icon className="h-4 w-4" />
                    </span>
                    {item.label}
                  </NavLink>
                )
              })}
              <hr className="my-3 border-slate-200" />
              <div className="flex items-center justify-between">
                <div className="text-sm">
                  <p className="text-slate-700 font-medium">{user?.full_name}</p>
                  <p className="text-xs text-slate-500 capitalize">{user?.role}</p>
                </div>
                {isSystemAdmin && (
                  <NavLink
                    to="/docs"
                    className="btn-secondary text-xs"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    Viewer Portal
                  </NavLink>
                )}
              </div>
              <button onClick={handleLogout} className="w-full btn-secondary">
                Sign Out
              </button>
            </div>
          </div>
        )}
      </header>
      )}

      {/* Main Content */}
      <main className="flex-1">
        <div className={`${isFullscreen ? 'px-0 py-0' : 'max-w-7xl mx-auto px-4 py-8'}`}>
          <Outlet />
        </div>
      </main>

      {/* Footer */}
      {!isFullscreen && (
      <footer className="border-t border-slate-200 bg-white/85 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-sm text-slate-500">
          <p>Developer Portal</p>
          <p className="text-xs mt-1">Internal documentation workspace</p>
        </div>
      </footer>
      )}
    </div>
  )
}
