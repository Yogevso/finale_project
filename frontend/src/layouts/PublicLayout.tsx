import { Outlet, Link, useNavigate } from 'react-router-dom'
import { FileText, Search, LogIn, Menu, X } from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '@/lib/auth'

export default function PublicLayout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const { user } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2">
              <FileText className="h-8 w-8 text-blue-600" />
              <span className="text-xl font-bold text-gray-900">DocPortal</span>
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-6">
              <Link 
                to="/browse" 
                className="text-gray-600 hover:text-gray-900 font-medium"
              >
                Browse Documents
              </Link>
              <Link 
                to="/search" 
                className="text-gray-600 hover:text-gray-900 font-medium flex items-center gap-1"
              >
                <Search className="h-4 w-4" />
                Search
              </Link>
            </nav>

            {/* Auth Button */}
            <div className="hidden md:flex items-center gap-4">
              {user ? (
                <button
                  onClick={() => navigate('/dashboard')}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 font-medium"
                >
                  Go to Dashboard
                </button>
              ) : (
                <Link
                  to="/login"
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 font-medium flex items-center gap-2"
                >
                  <LogIn className="h-4 w-4" />
                  Login
                </Link>
              )}
            </div>

            {/* Mobile menu button */}
            <button
              className="md:hidden p-2"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? (
                <X className="h-6 w-6 text-gray-600" />
              ) : (
                <Menu className="h-6 w-6 text-gray-600" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-gray-200">
            <div className="px-4 py-4 space-y-3">
              <Link
                to="/browse"
                className="block text-gray-600 hover:text-gray-900 font-medium"
                onClick={() => setMobileMenuOpen(false)}
              >
                Browse Documents
              </Link>
              <Link
                to="/search"
                className="block text-gray-600 hover:text-gray-900 font-medium"
                onClick={() => setMobileMenuOpen(false)}
              >
                Search
              </Link>
              <hr className="my-2" />
              {user ? (
                <button
                  onClick={() => {
                    setMobileMenuOpen(false)
                    navigate('/dashboard')
                  }}
                  className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 font-medium"
                >
                  Go to Dashboard
                </button>
              ) : (
                <Link
                  to="/login"
                  className="block w-full text-center bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 font-medium"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Login
                </Link>
              )}
            </div>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main>
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <FileText className="h-6 w-6 text-blue-600" />
                <span className="text-lg font-bold text-gray-900">DocPortal</span>
              </div>
              <p className="text-gray-500 text-sm">
                Your central hub for documentation and knowledge sharing.
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-3">Quick Links</h3>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link to="/browse" className="text-gray-500 hover:text-gray-900">
                    Browse All Documents
                  </Link>
                </li>
                <li>
                  <Link to="/search" className="text-gray-500 hover:text-gray-900">
                    Search
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-3">Access</h3>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link to="/login" className="text-gray-500 hover:text-gray-900">
                    Login for more content
                  </Link>
                </li>
              </ul>
            </div>
          </div>
          <div className="mt-8 pt-6 border-t border-gray-200 text-center text-sm text-gray-500">
            © {new Date().getFullYear()} DocPortal. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  )
}
