import { useAuth } from '@/lib/auth'
import { useNavigate, Link } from 'react-router-dom'
import NotificationBell from './NotificationBell'

export default function Header() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="sticky top-0 z-20 backdrop-blur bg-white/80 border-b border-slate-200">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/dashboard" className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-2xl bg-slate-900 text-white flex items-center justify-center font-semibold font-display">
              DP
            </div>
            <div>
              <div className="text-lg font-semibold text-slate-900 leading-tight font-display">Document Portal</div>
            </div>
          </Link>
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden md:flex items-center gap-2 text-sm">
            <span className="text-slate-500">Logged in as</span>
            <span className="font-medium text-slate-900">{user?.full_name}</span>
            <span className="pill capitalize">
              {user?.role}
            </span>
          </div>
          
          {/* Notification Bell */}
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
  )
}
