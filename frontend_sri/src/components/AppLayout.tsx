import { useState } from 'react'
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
  const [showLogoutDialog, setShowLogoutDialog] = useState(false)

  // Connect WebSocket globally when authenticated
  useGlobalWs()

  // Notification counts (only meaningful when authenticated)
  const { pendingInvites, incomingSOS } = useNotifications()

  function doLogout() {
    clearToken()
    setShowLogoutDialog(false)
    navigate('/login', { replace: true })
  }

  async function handleLogoutOffline() {
    try { await updatePresence('OFFLINE') } catch { /* ignore */ }
    doLogout()
  }

  function handleLogoutStayVisible() {
    // Keep current presence status — just log out without changing it
    doLogout()
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

              <Link to="/profile" className={navClass('/profile')}>
                Profile
              </Link>

              <Link to="/settings" className={navClass('/settings')}>
                Settings
              </Link>

              <button
                type="button"
                onClick={() => setShowLogoutDialog(true)}
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

      {/* Logout confirmation dialog */}
      {showLogoutDialog && (
        <div className="modal-overlay" onClick={() => setShowLogoutDialog(false)}>
          <div className="card" onClick={(e) => e.stopPropagation()} style={{
            maxWidth: 420, width: '90%', padding: '2rem', textAlign: 'center',
          }}>
            <h3 className="heading-md mb-3">Logout</h3>
            <p className="text-secondary text-sm mb-6">
              Do you want to stay visible on your buddies' radar after logging out?
            </p>
            <div className="flex-col gap-sm">
              <button className="btn btn-primary" onClick={handleLogoutStayVisible}>
                Stay on Radar &amp; Logout
              </button>
              <button className="btn btn-danger" onClick={handleLogoutOffline}>
                Go Offline &amp; Logout
              </button>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowLogoutDialog(false)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
