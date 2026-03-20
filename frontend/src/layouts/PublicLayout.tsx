import { Outlet, Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { Menu, Search, X } from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '@/lib/auth'
import AnnouncementBanner from '@/components/AnnouncementBanner'
import { SkipNavLink } from '@/components/a11y/SkipNavLink'

export default function PublicLayout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const { user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const isFullscreen = location.search.includes('fullscreen=1') || location.pathname.endsWith('/fullscreen')

  return (
    <div className="min-h-screen flex flex-col">
      <SkipNavLink />
      {/* Zip B Style Header */}
      {!isFullscreen && (
      <header className="sticky top-0 z-20 backdrop-blur bg-sky-100/85 border-b border-sky-200">
        <div className="container mx-auto px-4 py-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          {/* Logo */}
          <div className="flex items-center justify-between">
            <Link to="/" className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-2xl bg-slate-900 text-white flex items-center justify-center font-semibold font-display">
                DP
              </div>
              <div>
                <div className="text-xs uppercase tracking-widest text-slate-600">Viewer Portal</div>
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
            <NavLink 
              to="/docs"
              className={({ isActive }) =>
                `px-4 py-2 rounded-full transition-colors ${
                  isActive
                    ? 'bg-white text-sky-800 font-medium border border-sky-200'
                    : 'text-slate-600 hover:bg-white/80 hover:text-sky-800'
                }`
              }
            >
              Docs
            </NavLink>
            <NavLink 
              to="/platforms"
              className={({ isActive }) =>
                `px-4 py-2 rounded-full transition-colors ${
                  isActive
                    ? 'bg-white text-sky-800 font-medium border border-sky-200'
                    : 'text-slate-600 hover:bg-white/80 hover:text-sky-800'
                }`
              }
            >
              Platforms
            </NavLink>
            <NavLink 
              to="/tools"
              className={({ isActive }) =>
                `px-4 py-2 rounded-full transition-colors ${
                  isActive
                    ? 'bg-white text-sky-800 font-medium border border-sky-200'
                    : 'text-slate-600 hover:bg-white/80 hover:text-sky-800'
                }`
              }
            >
              Tools
            </NavLink>
            <NavLink 
              to="/help"
              className={({ isActive }) =>
                `px-4 py-2 rounded-full transition-colors ${
                  isActive
                    ? 'bg-white text-sky-800 font-medium border border-sky-200'
                    : 'text-slate-600 hover:bg-white/80 hover:text-sky-800'
                }`
              }
            >
              Help
            </NavLink>
          </nav>

          {/* Auth Button */}
          <div className="hidden md:flex items-center gap-3 text-sm">
            {user ? (
              <button
                onClick={() => navigate('/dashboard')}
                className="btn-primary"
              >
                Go to Dashboard
              </button>
            ) : (
              <>
                <span className="text-xs text-slate-700">External access to approved documentation</span>
                <Link to="/login" className="btn-primary">
                  Sign in
                </Link>
              </>
            )}
          </div>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-slate-200 bg-white">
            <div className="container mx-auto px-4 py-4 space-y-2">
              <NavLink
                to="/docs"
                className={({ isActive }) =>
                  `block px-4 py-2 rounded-xl transition-colors ${
                    isActive
                      ? 'bg-sky-100 text-sky-800 font-medium'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`
                }
                onClick={() => setMobileMenuOpen(false)}
              >
                Docs
              </NavLink>
              <NavLink
                to="/platforms"
                className={({ isActive }) =>
                  `block px-4 py-2 rounded-xl transition-colors ${
                    isActive
                      ? 'bg-sky-100 text-sky-800 font-medium'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`
                }
                onClick={() => setMobileMenuOpen(false)}
              >
                Platforms
              </NavLink>
              <NavLink
                to="/tools"
                className={({ isActive }) =>
                  `block px-4 py-2 rounded-xl transition-colors ${
                    isActive
                      ? 'bg-sky-100 text-sky-800 font-medium'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`
                }
                onClick={() => setMobileMenuOpen(false)}
              >
                Tools
              </NavLink>
              <NavLink
                to="/help"
                className={({ isActive }) =>
                  `block px-4 py-2 rounded-xl transition-colors ${
                    isActive
                      ? 'bg-sky-100 text-sky-800 font-medium'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`
                }
                onClick={() => setMobileMenuOpen(false)}
              >
                Help
              </NavLink>
              <hr className="my-3 border-slate-200" />
              {/* Mobile search (#70) */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-600" aria-hidden="true" />
                <input
                  type="search"
                  placeholder="Search documentation..."
                  className="input-field pl-9 w-full"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      const query = (e.target as HTMLInputElement).value
                      if (query) {
                        setMobileMenuOpen(false)
                        navigate(`/search?q=${encodeURIComponent(query)}`)
                      }
                    }
                  }}
                />
              </div>
              <hr className="my-3 border-slate-200" />
              {user ? (
                <button
                  onClick={() => {
                    setMobileMenuOpen(false)
                    navigate('/dashboard')
                  }}
                  className="w-full btn-primary"
                >
                  Go to Dashboard
                </button>
              ) : (
                <Link
                  to="/login"
                  className="block w-full text-center btn-primary"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Sign in
                </Link>
              )}
            </div>
          </div>
        )}
      </header>
      )}

      {/* Announcement Banner */}
      {!isFullscreen && <AnnouncementBanner />}

      {/* Main Content */}
      <main id="main-content" className="flex-1">
        <Outlet />
      </main>

      {/* Zip B Style Footer */}
      {!isFullscreen && (
      <footer className="border-t border-slate-200 bg-white/80 backdrop-blur">
        <div className="container mx-auto px-4 py-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="h-8 w-8 rounded-xl bg-slate-900 text-white flex items-center justify-center font-semibold text-sm font-display">
                  DP
                </div>
                <span className="text-lg font-semibold text-slate-900 font-display">Documentation Platform</span>
              </div>
              <p className="text-sm text-slate-700">
                Your central hub for documentation and knowledge sharing.
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-slate-900 mb-3 font-display">Quick Links</h3>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link to="/docs" className="text-slate-700 underline decoration-slate-300 underline-offset-4 transition-colors hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 rounded">
                    Docs Library
                  </Link>
                </li>
                <li>
                  <Link to="/platforms" className="text-slate-700 underline decoration-slate-300 underline-offset-4 transition-colors hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 rounded">
                    Platform History
                  </Link>
                </li>
                <li>
                  <Link to="/search" className="text-slate-700 underline decoration-slate-300 underline-offset-4 transition-colors hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 rounded">
                    Search
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-slate-900 mb-3 font-display">Access</h3>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link to="/login" className="text-slate-700 underline decoration-slate-300 underline-offset-4 transition-colors hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 rounded">
                    Login for more content
                  </Link>
                </li>
              </ul>
            </div>
          </div>
          <div className="mt-8 pt-6 border-t border-slate-200 text-center text-sm text-slate-700">
            © {new Date().getFullYear()} DocPortal. All rights reserved.
          </div>
        </div>
      </footer>
      )}
    </div>
  )
}
