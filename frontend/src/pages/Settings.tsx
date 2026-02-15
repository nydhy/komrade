import { useEffect, useState } from 'react'
import { getMySettings, updateMySettings, type UserSettings } from '../api/settings'

export default function Settings() {
  const [_settings, setSettings] = useState<UserSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  // Form state
  const [quietStart, setQuietStart] = useState('')
  const [quietEnd, setQuietEnd] = useState('')
  const [sharePrecise, setSharePrecise] = useState(true)

  async function load() {
    try {
      const data = await getMySettings()
      setSettings(data)
      setQuietStart(data.quiet_hours_start ?? '')
      setQuietEnd(data.quiet_hours_end ?? '')
      setSharePrecise(data.share_precise_location)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSuccess(false)
    try {
      const data = await updateMySettings({
        quiet_hours_start: quietStart || null,
        quiet_hours_end: quietEnd || null,
        share_precise_location: sharePrecise,
      })
      setSettings(data)
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  function openCrisisResources() {
    window.dispatchEvent(new Event('open-crisis-resources'))
  }

  function showPrivacyNotice() {
    window.dispatchEvent(new Event('show-privacy-banner'))
  }

  if (loading) {
    return (
      <div className="page-container flex-center" style={{ minHeight: '40vh' }}>
        <p className="text-secondary">Loading settings...</p>
      </div>
    )
  }

  return (
    <div className="page-container page-container-narrow">
      <div className="animate-in mb-8">
        <h1 className="heading-lg mb-2">Settings</h1>
        <p className="text-muted">Manage your preferences and privacy</p>
      </div>

      {error && (
        <div className="alert alert-danger animate-in mb-4">
          {error}
        </div>
      )}

      {success && (
        <div className="alert alert-success animate-in mb-4">
          Settings saved successfully.
        </div>
      )}

      <form onSubmit={handleSave} className="flex-col gap-lg">
        {/* Quiet Hours */}
        <section className="card animate-in animate-in-delay-1">
          <h2 className="heading-md mb-2">Quiet Hours</h2>
          <p className="text-muted text-sm mb-4">
            During quiet hours, you won't be selected as an SOS recipient.
          </p>
          <div className="divider mb-4" />
          <div className="form-row">
            <div className="input-group">
              <label>Start</label>
              <input
                type="time"
                className="input"
                value={quietStart}
                onChange={(e) => setQuietStart(e.target.value)}
              />
            </div>
            <div className="input-group">
              <label>End</label>
              <input
                type="time"
                className="input"
                value={quietEnd}
                onChange={(e) => setQuietEnd(e.target.value)}
              />
            </div>
          </div>
          {quietStart && (
            <div className="mt-3">
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => { setQuietStart(''); setQuietEnd('') }}
              >
                Clear quiet hours
              </button>
            </div>
          )}
        </section>

        {/* Location Privacy */}
        <section className="card animate-in animate-in-delay-2">
          <h2 className="heading-md mb-2">Location Privacy</h2>
          <p className="text-muted text-sm mb-4">
            When disabled, buddies see approximate location only until they accept an SOS.
          </p>
          <div className="divider mb-4" />
          <label className="checkbox-toggle">
            <input
              type="checkbox"
              checked={sharePrecise}
              onChange={(e) => setSharePrecise(e.target.checked)}
            />
            <span className="toggle-track" />
            <span className="toggle-label">Share precise location</span>
          </label>
        </section>

        {/* Privacy & Terms */}
        <section className="card animate-in animate-in-delay-3">
          <h2 className="heading-md mb-2">Privacy & Disclaimers</h2>
          <p className="text-muted text-sm mb-4">
            Transparency around data handling and mental health support boundaries.
          </p>
          <div className="divider mb-4" />

          <div className="privacy-card">
            <div className="privacy-card-header">
              <span className="privacy-card-icon" aria-hidden>🔒</span>
              <h4>Your Data is Private</h4>
            </div>
            <p>
              Your data is encrypted and stored securely. We never sell or share your personal
              information with third parties. You can control your data visibility from settings.
            </p>
            <button type="button" className="btn btn-secondary btn-small" onClick={showPrivacyNotice}>
              Show Privacy Notice
            </button>
          </div>

          <div className="privacy-card">
            <div className="privacy-card-header">
              <span className="privacy-card-icon" aria-hidden>🏥</span>
              <h4>Medical Disclaimer</h4>
            </div>
            <p>
              Komrade is a wellness and skill-building tool designed to complement professional
              mental health care. It is not a substitute for therapy, counseling, or medical treatment.
            </p>
          </div>

          <div className="privacy-card">
            <div className="privacy-card-header">
              <span className="privacy-card-icon" aria-hidden>📞</span>
              <h4>Crisis Resources</h4>
            </div>
            <p>
              If you&apos;re experiencing a mental health crisis, immediate help is available 24/7
              through the Veterans Crisis Line.
            </p>
            <button type="button" className="btn btn-secondary btn-small" onClick={openCrisisResources}>
              View Crisis Resources
            </button>
          </div>
        </section>

        {/* Save */}
        <div className="animate-in animate-in-delay-4">
          <button
            type="submit"
            className="btn btn-primary btn-lg"
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </form>
    </div>
  )
}
