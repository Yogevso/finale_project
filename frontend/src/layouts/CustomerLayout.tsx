/**
 * CustomerLayout - Layout for customer portal (authenticated customers)
 * Restyled with Zip B design system
 */
import { useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Menu, Search, X, HelpCircle } from 'lucide-react'

import { getNavigationForRole } from '@/config/routes'
import { useAuth } from '@/lib/auth'
import NpsWidget from '@/components/NpsWidget'
import AssistantChatBubble from '@/components/AssistantChatBubble'
import { SkipNavLink } from '@/components/a11y/SkipNavLink'

export default function CustomerLayout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const { user, logout } = useAuth()
  const navigation = getNavigationForRole(user?.role || null)
  const location = useLocation()
  const navigate = useNavigate()
  const isFullscreen = location.search.includes('fullscreen=1') || location.pathname.endsWith('/fullscreen')

  const handleLogout = () => {
    logout()
    navigate('/docs')
  }

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-slate-50 to-sky-50">
      <SkipNavLink />
      {/* Intel-like Header */}
      {!isFullscreen && (
      <header className="sticky top-0 z-20 backdrop-blur bg-sky-100/85 border-b border-sky-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          {/* Logo */}
          <div className="flex items-center justify-between">
            <Link to="/portal/dashboard" className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-2xl bg-slate-900 text-white flex items-center justify-center font-semibold font-display">
                DP
              </div>
              <div>
                <div className="text-xs uppercase tracking-widest text-slate-500">Customer Portal</div>
                <div className="text-lg font-semibold text-slate-900 leading-tight font-display">Developer Portal</div>
              </div>
            </Link>

            {/* Mobile menu button */}
            <button
              className="md:hidden p-2 rounded-lg hover:bg-slate-100"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              aria-expanded={mobileMenuOpen}
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
            {navigation.map((item) => {
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

          {/* Search & User */}
          <div className="hidden md:flex items-center gap-4">
            {/* Search bar */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="search"
                placeholder="Search documents..."
                className="input-field pl-9 w-48 lg:w-64 bg-white"
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
              <span className="pill bg-white border-sky-200">Customer</span>
            </div>

            <button onClick={handleLogout} className="btn-ghost">
              Sign Out
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-sky-200 bg-sky-50/90">
            <div className="max-w-7xl mx-auto px-4 py-4 space-y-2">
              {navigation.map((item) => {
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
      )}

      {/* Main Content */}
      <main id="main-content" className="flex-1">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <Outlet />
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white/85 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-slate-500">
            <p>Customer Portal</p>
            <nav className="flex items-center gap-4" aria-label="Footer">
              <Link to="/portal/support" className="hover:text-sky-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 rounded">Support</Link>
              <Link to="/portal/documents" className="hover:text-sky-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 rounded">Documents</Link>
              <span className="text-slate-300">|</span>
              <span className="text-xs">&copy; {new Date().getFullYear()} Developer Portal</span>
            </nav>
          </div>
        </div>
      </footer>

      {/* NPS Feedback Widget (Y2-019) */}
      <div className="z-30">
        <NpsWidget />
      </div>

      {/* AI Assistant Chat Bubble */}
      <AssistantChatBubble />

      {/* Floating Help Button (X1-092) — shifted left to not overlap chat bubble */}
      {!isFullscreen && (
        <Link
          to="/portal/support"
          className="fixed bottom-6 right-20 z-30 flex h-12 w-12 items-center justify-center rounded-full bg-sky-600 text-white shadow-lg transition-transform hover:scale-110 hover:bg-sky-700"
          title="Need help? Contact support"
        >
          <HelpCircle className="h-6 w-6" />
        </Link>
      )}
    </div>
  )
}
