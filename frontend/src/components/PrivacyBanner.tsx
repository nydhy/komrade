import { useEffect, useState } from 'react'

const PRIVACY_BANNER_KEY = 'privacy-banner-dismissed'

export function PrivacyBanner() {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    setIsVisible(!localStorage.getItem(PRIVACY_BANNER_KEY))
  }, [])

  useEffect(() => {
    function handleShowBanner() {
      localStorage.removeItem(PRIVACY_BANNER_KEY)
      setIsVisible(true)
    }
    window.addEventListener('show-privacy-banner', handleShowBanner)
    return () => window.removeEventListener('show-privacy-banner', handleShowBanner)
  }, [])

  function handleDismiss() {
    localStorage.setItem(PRIVACY_BANNER_KEY, 'true')
    setIsVisible(false)
  }

  if (!isVisible) return null

  return (
    <div className="privacy-banner" role="status" aria-live="polite">
      <div className="privacy-banner-content">
        <div className="privacy-icon" aria-hidden>🔒</div>
        <div className="privacy-text">
          <strong>Your privacy matters.</strong> Your data is encrypted and private.
          {' '}We never share your information with anyone.
        </div>
        <button
          className="privacy-dismiss"
          onClick={handleDismiss}
          aria-label="Dismiss privacy notice"
          type="button"
        >
          Got it
        </button>
      </div>
    </div>
  )
}

