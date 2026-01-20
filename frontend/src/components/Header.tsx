import { useAuth } from '@/lib/auth'
import { useNavigate } from 'react-router-dom'
import NotificationBell from './NotificationBell'

export default function Header() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="fixed top-0 left-0 right-0 h-16 bg-white border-b border-gray-200 z-50">
      <div className="flex items-center justify-between h-full px-6">
        <div className="flex items-center space-x-4">
          <h1 className="text-xl font-bold text-blue-600">Document Portal V2</h1>
        </div>

        <div className="flex items-center space-x-4">
          <div className="text-sm">
            <span className="text-gray-500">Logged in as </span>
            <span className="font-medium text-gray-900">{user?.full_name}</span>
            <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-700 capitalize">
              {user?.role}
            </span>
          </div>
          
          {/* Notification Bell */}
          <NotificationBell />
          
          <button
            onClick={handleLogout}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
          >
            Logout
          </button>
        </div>
      </div>
    </header>
  )
}
