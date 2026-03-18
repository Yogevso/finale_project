import { useEffect, useRef, useState } from 'react'
import { ChevronRight, Menu, X } from 'lucide-react'
import { NavLink, Outlet, useLocation, useNavigate, Link } from 'react-router-dom'

import { getNavigationForRole } from '@/config/routes'
import { useAuth } from '@/lib/auth'
import { useChatUnreadCount } from '@/features/chat/useChatUnreadCount'

import GlobalSearchBar from './GlobalSearchBar'
import NotificationBell from './NotificationBell'
import AnnouncementBanner from './AnnouncementBanner'
import AssistantChatBubble from './AssistantChatBubble'
import { SkipNavLink } from './a11y/SkipNavLink'

export default function Layout() {
  const { user, logout, isSystemAdmin } = useAuth()
  const navigate = useNavigate()
  const navItems = getNavigationForRole(user?.role || null)
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const mobileMenuRef = useRef<HTMLDivElement>(null)
  const isFullscreen = location.search.includes('fullscreen=1') || location.pathname.endsWith('/fullscreen')
  const chatUnreadCount = useChatUnreadCount()

  useEffect(() => {
    setMobileMenuOpen(false)
  }, [location.pathname, location.search])

  // #65 — Focus trap for mobile menu
  useEffect(() => {
    if (!mobileMenuOpen || !mobileMenuRef.current) return
    const menu = mobileMenuRef.current
    const focusable = menu.querySelectorAll<HTMLElement>('a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])')
    if (focusable.length === 0) return
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    first.focus()
    const trap = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { setMobileMenuOpen(false); return }
      if (e.key !== 'Tab') return
      if (e.shiftKey) { if (document.activeElement === first) { e.preventDefault(); last.focus() } }
      else { if (document.activeElement === last) { e.preventDefault(); first.focus() } }
    }
    menu.addEventListener('keydown', trap)
    return () => menu.removeEventListener('keydown', trap)
  }, [mobileMenuOpen])

  // #64 — Breadcrumb segments
  const breadcrumbs = location.pathname
    .split('/')
    .filter(Boolean)
    .reduce<{ label: string; path: string }[]>((acc, segment, i, arr) => {
      const path = '/' + arr.slice(0, i + 1).join('/')
      const label = segment
        .replace(/[-_]/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase())
      acc.push({ label, path })
      return acc
    }, [])

  const handleLogout = () => {
    logout()
    navigate('/docs')
  }

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-slate-50 to-sky-50">
      <SkipNavLink />
      {/* Intel-like Header */}
      {!isFullscreen && (
      <header className="app-shell-header sticky top-0 z-20 backdrop-blur bg-sky-100/85 border-b border-sky-200">
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
                aria-expanded={mobileMenuOpen}
              >
                <span className="relative block h-5 w-5">
                  <X className={`absolute inset-0 h-5 w-5 text-slate-600 transition-all duration-200 ${mobileMenuOpen ? 'opacity-100 rotate-0' : 'opacity-0 rotate-90'}`} />
                  <Menu className={`absolute inset-0 h-5 w-5 text-slate-600 transition-all duration-200 ${mobileMenuOpen ? 'opacity-0 -rotate-90' : 'opacity-100 rotate-0'}`} />
                </span>
              </button>
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1 text-sm" aria-label="Primary">
            {navItems.map((item) => {
              const Icon = item.icon
              const badge = item.path === '/chat' && chatUnreadCount > 0 ? chatUnreadCount : 0
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `relative px-4 py-2 rounded-full transition-colors ${
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
                  {badge > 0 && (
                    <span className="absolute -top-1 -right-1 flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white" aria-label={`${badge} unread messages`}>
                      <span aria-hidden="true">{badge > 99 ? '99+' : badge}</span>
                    </span>
                  )}
                </NavLink>
              )
            })}
          </nav>

          {/* Global Search (Y2-001) */}
          <div className="hidden md:flex">
            <GlobalSearchBar />
          </div>

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
          <div ref={mobileMenuRef} className="md:hidden border-t border-sky-200 bg-sky-50/90">
            <div className="max-w-7xl mx-auto px-4 py-4 space-y-2">
              {navItems.map((item) => {
                const Icon = item.icon
                const badge = item.path === '/chat' && chatUnreadCount > 0 ? chatUnreadCount : 0
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
                    {badge > 0 && (
                      <span className="ml-auto flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                        {badge > 99 ? '99+' : badge}
                      </span>
                    )}
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

      {/* Announcement Banner */}
      {!isFullscreen && <AnnouncementBanner />}

      {/* Breadcrumb (#64) */}
      {!isFullscreen && breadcrumbs.length > 1 && (
        <nav aria-label="Breadcrumb" className="max-w-7xl mx-auto px-4 pt-4">
          <ol className="flex items-center gap-1 text-sm text-slate-500">
            <li><Link to="/dashboard" className="hover:text-sky-700 transition-colors">Home</Link></li>
            {breadcrumbs.map((crumb, i) => (
              <li key={crumb.path} className="flex items-center gap-1">
                <ChevronRight className="h-3.5 w-3.5" />
                {i === breadcrumbs.length - 1 ? (
                  <span className="font-medium text-slate-700">{crumb.label}</span>
                ) : (
                  <Link to={crumb.path} className="hover:text-sky-700 transition-colors">{crumb.label}</Link>
                )}
              </li>
            ))}
          </ol>
        </nav>
      )}

      {/* Main Content */}
      <main id="main-content" className="app-shell-main flex-1">
        <div className={`${isFullscreen ? 'px-0 py-0' : 'max-w-7xl mx-auto px-4 py-8'}`}>
          <Outlet />
        </div>
      </main>

      {/* Footer */}
      {!isFullscreen && (
      <footer className="app-shell-footer border-t border-slate-200 bg-white/85 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-slate-500">
            <p>Developer Portal &mdash; Internal documentation workspace</p>
            <nav className="flex items-center gap-4" aria-label="Footer">
              <Link to="/help" className="hover:text-sky-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 rounded">Help</Link>
              <Link to="/docs" className="hover:text-sky-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 rounded">Documentation</Link>
              <span className="text-slate-300">|</span>
              <span className="text-xs">&copy; {new Date().getFullYear()} DocPortal</span>
            </nav>
          </div>
        </div>
      </footer>
      )}

      {/* AI Assistant Chat Bubble */}
      <AssistantChatBubble />
    </div>
  )
}
