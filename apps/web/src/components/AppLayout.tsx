import { Link, useNavigate, useLocation } from 'react-router-dom'
import { isAuthenticated, clearToken } from '../state/authStore'
import { useGlobalWs } from '../state/realtime'
import { useNotifications } from '../context/NotificationContext'
import { updatePresence } from '../api/presence'

interface AppLayoutProps {
  children: React.ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const authenticated = isAuthenticated()

  // Connect WebSocket globally when authenticated
  useGlobalWs()

  // Notification counts (only meaningful when authenticated)
  const { pendingInvites, incomingSOS } = useNotifications()

  async function handleLogout() {
    try { await updatePresence('OFFLINE') } catch { /* ignore */ }
    clearToken()
    navigate('/login', { replace: true })
  }

  function navClass(path: string) {
    const isActive =
      path === '/' ? location.pathname === '/' : location.pathname.startsWith(path)
    return `nav-link${isActive ? ' active' : ''}`
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <Link to="/" className="heading-md text-gradient">
          VetBridge
        </Link>

        <nav className="flex-center gap-sm">
          {authenticated ? (
            <>
              <Link to="/" className={navClass('/')}>
                Dashboard
              </Link>

              <span className="nav-badge-wrapper">
                <Link to="/buddies" className={navClass('/buddies')}>
                  My Buddies
                </Link>
                {pendingInvites > 0 && (
                  <span className="badge-notification">{pendingInvites}</span>
                )}
              </span>

              <Link to="/map" className={navClass('/map')}>
                Map
              </Link>

              <span className="nav-badge-wrapper">
                <Link to="/inbox" className={navClass('/inbox')}>
                  Inbox
                </Link>
                {incomingSOS > 0 && (
                  <span className="badge-notification">{incomingSOS}</span>
                )}
              </span>

              <Link to="/sos-history" className={navClass('/sos-history')}>
                SOS History
              </Link>

              <Link to="/ladder" className={navClass('/ladder')}>
                Ladder
              </Link>

              <Link to="/translate" className={navClass('/translate')}>
                Translate
              </Link>

              <Link to="/profile" className={navClass('/profile')}>
                Profile
              </Link>

              <Link to="/settings" className={navClass('/settings')}>
                Settings
              </Link>

              <button
                type="button"
                onClick={handleLogout}
                className="btn btn-ghost btn-sm"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className={navClass('/login')}>
                Login
              </Link>
              <Link to="/register" className={navClass('/register')}>
                Register
              </Link>
            </>
          )}
        </nav>
      </header>

      <main className="app-main">{children}</main>
    </div>
  )
}
