/**
 * CustomerLayout - Layout for customer portal (authenticated customers)
 * Restyled with Zip B design system
 */
import { useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import {
  Menu,
  X,
  Search,
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/portal/dashboard', icon: '📊' },
  { name: 'Documents', href: '/portal/documents', icon: '📄' },
  { name: 'My Feedback', href: '/portal/feedback', icon: '💬' },
]

export default function CustomerLayout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const { user, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/docs')
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Zip B Style Header */}
      <header className="sticky top-0 z-20 backdrop-blur bg-white/80 border-b border-slate-200">
        <div className="container mx-auto px-4 py-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          {/* Logo */}
          <div className="flex items-center justify-between">
            <Link to="/portal/dashboard" className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-2xl bg-slate-900 text-white flex items-center justify-center font-semibold font-display">
                DP
              </div>
              <div>
                <div className="text-sm text-slate-500">Customer</div>
                <div className="text-lg font-semibold text-slate-900 leading-tight font-display">Documentation Platform</div>
              </div>
            </Link>
            
            {/* Mobile menu button */}
            <button
              className="md:hidden p-2 rounded-lg hover:bg-slate-100"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? (
                <X className="h-6 w-6 text-slate-600" />
              ) : (
                <Menu className="h-6 w-6 text-slate-600" />
              )}
            </button>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1 text-sm" aria-label="Primary">
            {navigation.map((item) => (
              <NavLink
                key={item.href}
                to={item.href}
                className={({ isActive }) =>
                  `px-4 py-2 rounded-full transition-colors ${
                    isActive
                      ? 'bg-sky-100 text-sky-800 font-medium'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }`
                }
              >
                <span className="mr-1.5">{item.icon}</span>
                {item.name}
              </NavLink>
            ))}
          </nav>

          {/* Search & User */}
          <div className="hidden md:flex items-center gap-4">
            {/* Search bar */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="search"
                placeholder="Search documents..."
                className="input-field pl-9 w-64"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    const query = (e.target as HTMLInputElement).value
                    if (query) {
                      navigate(`/portal/documents?search=${encodeURIComponent(query)}`)
                    }
                  }
                }}
              />
            </div>
            
            {/* User info */}
            <div className="flex items-center gap-2 text-sm">
              <span className="text-slate-500">{user?.full_name || user?.email}</span>
              <span className="pill">Customer</span>
            </div>
            
            <button onClick={handleLogout} className="btn-ghost">
              Sign Out
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-slate-200 bg-white">
            <div className="container mx-auto px-4 py-4 space-y-2">
              {navigation.map((item) => (
                <NavLink
                  key={item.href}
                  to={item.href}
                  className={({ isActive }) =>
                    `flex items-center px-4 py-2 rounded-xl transition-colors ${
                      isActive
                        ? 'bg-sky-100 text-sky-800 font-medium'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`
                  }
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <span className="mr-2">{item.icon}</span>
                  {item.name}
                </NavLink>
              ))}
              <hr className="my-3 border-slate-200" />
              {/* Mobile search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <input
                  type="search"
                  placeholder="Search documents..."
                  className="input-field pl-9"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      const query = (e.target as HTMLInputElement).value
                      if (query) {
                        setMobileMenuOpen(false)
                        navigate(`/portal/documents?search=${encodeURIComponent(query)}`)
                      }
                    }
                  }}
                />
              </div>
              <div className="pt-2">
                <button onClick={handleLogout} className="w-full btn-secondary">
                  Sign Out
                </button>
              </div>
            </div>
          </div>
        )}
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
          <p>Customer Portal</p>
          <p className="text-xs mt-1">© {new Date().getFullYear()} DocPortal. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}
