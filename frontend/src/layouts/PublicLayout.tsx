import { Outlet, Link, NavLink, useNavigate } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '@/lib/auth'

export default function PublicLayout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const { user } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex flex-col">
      {/* Zip B Style Header */}
      <header className="sticky top-0 z-20 backdrop-blur bg-white/80 border-b border-slate-200">
        <div className="container mx-auto px-4 py-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          {/* Logo */}
          <div className="flex items-center justify-between">
            <Link to="/" className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-2xl bg-slate-900 text-white flex items-center justify-center font-semibold font-display">
                DP
              </div>
              <div>
                <div className="text-sm text-slate-500">Viewer</div>
                <div className="text-lg font-semibold text-slate-900 leading-tight font-display">Document Portal</div>
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
            <NavLink 
              to="/browse"
              className={({ isActive }) =>
                `px-4 py-2 rounded-full transition-colors ${
                  isActive
                    ? 'bg-sky-100 text-sky-800 font-medium'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`
              }
            >
              Browse
            </NavLink>
            <NavLink 
              to="/search"
              className={({ isActive }) =>
                `px-4 py-2 rounded-full transition-colors ${
                  isActive
                    ? 'bg-sky-100 text-sky-800 font-medium'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`
              }
            >
              Search
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
              <Link to="/login" className="btn-primary">
                Sign In
              </Link>
            )}
          </div>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-slate-200 bg-white">
            <div className="container mx-auto px-4 py-4 space-y-2">
              <NavLink
                to="/browse"
                className={({ isActive }) =>
                  `block px-4 py-2 rounded-xl transition-colors ${
                    isActive
                      ? 'bg-sky-100 text-sky-800 font-medium'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`
                }
                onClick={() => setMobileMenuOpen(false)}
              >
                Browse Documents
              </NavLink>
              <NavLink
                to="/search"
                className={({ isActive }) =>
                  `block px-4 py-2 rounded-xl transition-colors ${
                    isActive
                      ? 'bg-sky-100 text-sky-800 font-medium'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`
                }
                onClick={() => setMobileMenuOpen(false)}
              >
                Search
              </NavLink>
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
                  Sign In
                </Link>
              )}
            </div>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* Zip B Style Footer */}
      <footer className="border-t border-slate-200 bg-white/80 backdrop-blur">
        <div className="container mx-auto px-4 py-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="h-8 w-8 rounded-xl bg-slate-900 text-white flex items-center justify-center font-semibold text-sm font-display">
                  DP
                </div>
                <span className="text-lg font-semibold text-slate-900 font-display">DocPortal</span>
              </div>
              <p className="text-slate-500 text-sm">
                Your central hub for documentation and knowledge sharing.
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-slate-900 mb-3 font-display">Quick Links</h3>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link to="/browse" className="text-slate-500 hover:text-slate-900 transition-colors">
                    Browse All Documents
                  </Link>
                </li>
                <li>
                  <Link to="/search" className="text-slate-500 hover:text-slate-900 transition-colors">
                    Search
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-slate-900 mb-3 font-display">Access</h3>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link to="/login" className="text-slate-500 hover:text-slate-900 transition-colors">
                    Login for more content
                  </Link>
                </li>
              </ul>
            </div>
          </div>
          <div className="mt-8 pt-6 border-t border-slate-200 text-center text-sm text-slate-500">
            © {new Date().getFullYear()} DocPortal. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  )
}
