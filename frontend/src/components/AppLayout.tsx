import { useEffect, useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { isAuthenticated, clearToken } from '../state/authStore'
import { useGlobalWs } from '../state/realtime'
import { useNotifications } from '../context/NotificationContext'
import { updatePresence } from '../api/presence'
import { BrandLogo } from './BrandLogo'
import { PrivacyBanner } from './PrivacyBanner'
import { DisclaimerFooter } from './DisclaimerFooter'

interface AppLayoutProps {
  children: React.ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const authenticated = isAuthenticated()
  const [showCrisisResources, setShowCrisisResources] = useState(false)

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

  useEffect(() => {
    if (!showCrisisResources) return
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setShowCrisisResources(false)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [showCrisisResources])

  useEffect(() => {
    function handleOpenCrisisResources() {
      setShowCrisisResources(true)
    }
    window.addEventListener('open-crisis-resources', handleOpenCrisisResources)
    return () => window.removeEventListener('open-crisis-resources', handleOpenCrisisResources)
  }, [])

  return (
    <div className="app-container">
      <PrivacyBanner />
      <header className="app-header">
        <Link to="/" className="brand-logo-link" aria-label="komrade home">
          <BrandLogo variant="header" />
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

              <Link to="/journey" className={navClass('/journey')}>
                Journey
              </Link>

              <Link to="/translate" className={navClass('/translate')}>
                Chat
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
          <button
            type="button"
            className="nav-crisis-btn"
            onClick={() => setShowCrisisResources(true)}
          >
            Need Help Now?
          </button>
        </nav>
      </header>

      <main className="app-main">{children}</main>
      <DisclaimerFooter />

      {showCrisisResources && (
        <div
          className="crisis-help-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="crisis-help-title"
          onClick={() => setShowCrisisResources(false)}
        >
          <div className="crisis-help-modal" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className="crisis-close"
              onClick={() => setShowCrisisResources(false)}
              aria-label="Close help modal"
            >
              ✕
            </button>

            <div className="crisis-help-header">
              <h2 id="crisis-help-title">Need Help Now?</h2>
            </div>
            <p className="crisis-help-note">
              You&apos;re not alone. Help is available right now.
            </p>

            <div className="crisis-section">
              <div className="crisis-section-label">Immediate Crisis Support</div>
              <div className="crisis-primary-action">
                <div className="crisis-primary-icon">📞</div>
                <div className="crisis-primary-content">
                  <div className="crisis-primary-title">Veterans Crisis Line</div>
                  <div className="crisis-primary-number">988 → press 1</div>
                  <div className="crisis-primary-subtitle">24/7 • Confidential • Free</div>
                </div>
                <a className="crisis-call-button" href="tel:988">Call Now</a>
              </div>

              <div className="crisis-secondary-options">
                <a className="crisis-option" href="sms:838255">💬 Text: 838255</a>
                <a
                  className="crisis-option"
                  href="https://www.veteranscrisisline.net/get-help-now/chat/"
                  target="_blank"
                  rel="noreferrer noopener"
                >
                  💻 Web Chat
                </a>
              </div>
            </div>

            <div className="crisis-divider" />

            <div className="crisis-section">
              <div className="crisis-section-label">Additional Resources</div>
              <div className="crisis-links">
                <a
                  className="crisis-resource"
                  href="https://www.va.gov/health-care/health-needs-conditions/mental-health/"
                  target="_blank"
                  rel="noreferrer noopener"
                >
                  <span>VA Mental Health Resources</span>
                  <span className="crisis-resource-arrow">→</span>
                </a>
                <a
                  className="crisis-resource"
                  href="https://www.va.gov/find-locations/"
                  target="_blank"
                  rel="noreferrer noopener"
                >
                  <span>Find nearby VA support locations</span>
                  <span className="crisis-resource-arrow">→</span>
                </a>
                <a
                  className="crisis-resource"
                  href="https://www.211.org/"
                  target="_blank"
                  rel="noreferrer noopener"
                >
                  <span>Local community support (211)</span>
                  <span className="crisis-resource-arrow">→</span>
                </a>
              </div>
            </div>

            <div className="crisis-911-warning">
              🚨 <strong>Immediate danger?</strong> Call 911 now.
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
