import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { register, login, type RegisterRequest } from '../api/auth'
import { setToken } from '../state/authStore'
import { searchAddress, type GeocodeSuggestion } from '../api/geocode'

const STEPS = ['Account', 'Role', 'Location'] as const

function getPasswordStrength(pw: string): { label: string; color: string; width: string } {
  if (pw.length === 0) return { label: '', color: '#e0e0e0', width: '0%' }
  let score = 0
  if (pw.length >= 6) score++
  if (pw.length >= 10) score++
  if (/[A-Z]/.test(pw)) score++
  if (/[0-9]/.test(pw)) score++
  if (/[^A-Za-z0-9]/.test(pw)) score++
  if (score <= 1) return { label: 'Weak', color: '#e53935', width: '20%' }
  if (score === 2) return { label: 'Fair', color: '#fb8c00', width: '40%' }
  if (score === 3) return { label: 'Good', color: '#fdd835', width: '60%' }
  if (score === 4) return { label: 'Strong', color: '#43a047', width: '80%' }
  return { label: 'Excellent', color: '#1b5e20', width: '100%' }
}

export default function Register() {
  const [step, setStep] = useState(0)
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [role, setRole] = useState<'veteran' | 'buddy'>('veteran')
  const [latitude, setLatitude] = useState<number | null>(null)
  const [longitude, setLongitude] = useState<number | null>(null)
  const [addressQuery, setAddressQuery] = useState('')
  const [selectedAddress, setSelectedAddress] = useState('')
  const [suggestions, setSuggestions] = useState<GeocodeSuggestion[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [geoLoading, setGeoLoading] = useState(false)
  const [geoError, setGeoError] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const navigate = useNavigate()

  const pwStrength = getPasswordStrength(password)
  const passwordsMatch = confirmPassword.length === 0 || password === confirmPassword

  function canAdvance(): boolean {
    if (step === 0) {
      return fullName.trim().length >= 2 && email.includes('@') && password.length >= 6 && password === confirmPassword
    }
    if (step === 1) return true
    return true
  }

  async function handleAddressSearch(query: string) {
    setAddressQuery(query)
    setSearchLoading(true)
    const results = await searchAddress(query)
    setSuggestions(results)
    setSearchLoading(false)
  }

  function handleSelectSuggestion(s: GeocodeSuggestion) {
    setLatitude(s.lat)
    setLongitude(s.lon)
    setSelectedAddress(s.display_name)
    setAddressQuery(s.display_name)
    setSuggestions([])
  }

  async function handleAutoDetect() {
    setGeoLoading(true)
    setGeoError('')
    try {
      // IP-based geolocation — works on all devices, no permissions needed
      const res = await fetch('https://ipapi.co/json/')
      if (!res.ok) throw new Error('IP geolocation service unavailable')
      const data = await res.json()
      if (data.latitude && data.longitude) {
        setLatitude(data.latitude)
        setLongitude(data.longitude)
        const addr = [data.city, data.region, data.country_name].filter(Boolean).join(', ')
        setSelectedAddress(addr || `${data.latitude.toFixed(4)}, ${data.longitude.toFixed(4)}`)
        setAddressQuery(addr || '')
      } else {
        throw new Error('Could not determine location')
      }
    } catch (err) {
      setGeoError(err instanceof Error ? err.message : 'Auto-detect failed. Please type your address above.')
    } finally {
      setGeoLoading(false)
    }
  }

  async function handleSubmit() {
    setError('')
    setLoading(true)
    try {
      const data: RegisterRequest = {
        email,
        password,
        full_name: fullName,
        role,
        latitude: latitude ?? undefined,
        longitude: longitude ?? undefined,
      }
      await register(data)
      const res = await login({ email, password })
      setToken(res.access_token)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="ambient-bg flex-center" style={{ minHeight: '100vh', padding: '2rem 1rem' }}>
      <div className="card glow-border animate-in" style={{ width: '100%', maxWidth: 480 }}>
        {/* Header */}
        <div className="text-center mb-6">
          <h1 className="heading-xl text-gradient mb-2">VetBridge</h1>
          <p className="text-muted text-sm">Join the veteran support network</p>

          {/* Step indicator */}
          <div className="flex-center gap-2 mt-6" style={{ gap: 8 }}>
            {STEPS.map((s, i) => (
              <div key={s} className="flex-center" style={{ gap: 8 }}>
                <div
                  className="flex-center"
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: '50%',
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    backgroundColor: i <= step ? 'var(--accent-primary)' : 'var(--bg-glass)',
                    color: i <= step ? '#fff' : 'var(--text-muted)',
                    boxShadow: i <= step ? '0 0 12px rgba(129, 140, 248, 0.5)' : 'none',
                    transition: 'all 0.3s',
                  }}
                >
                  {i < step ? '\u2713' : i + 1}
                </div>
                <span
                  className="text-sm"
                  style={{
                    fontWeight: 600,
                    color: i <= step ? 'var(--text-primary)' : 'var(--text-muted)',
                  }}
                >
                  {s}
                </span>
                {i < STEPS.length - 1 && (
                  <div
                    style={{
                      width: 24,
                      height: 2,
                      backgroundColor: i < step ? 'var(--accent-primary)' : 'var(--border-default)',
                      borderRadius: 1,
                    }}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        <hr className="divider" />

        {/* Body */}
        <div className="p-4">
          {/* STEP 0: Account Details */}
          {step === 0 && (
            <div>
              <h2 className="heading-md mb-6">Create your account</h2>

              <div className="input-group mb-4">
                <label>Full Name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="John Doe"
                  required
                  className="input"
                />
              </div>

              <div className="input-group mb-4">
                <label>Email Address</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="john@example.com"
                  required
                  autoComplete="email"
                  className="input"
                />
              </div>

              <div className="input-group mb-4">
                <label>Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Min. 6 characters"
                    required
                    autoComplete="new-password"
                    className="input"
                    style={{ paddingRight: '3rem' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="btn btn-ghost btn-sm absolute"
                    style={{ right: 8, top: '50%', transform: 'translateY(-50%)' }}
                  >
                    {showPassword ? 'Hide' : 'Show'}
                  </button>
                </div>
                {password.length > 0 && (
                  <div className="mt-2">
                <div
                  className="overflow-hidden"
                  style={{ height: 4, borderRadius: 2, backgroundColor: 'var(--border-default)' }}
                >
                      <div
                        style={{
                          height: '100%',
                          width: pwStrength.width,
                          backgroundColor: pwStrength.color,
                          borderRadius: 2,
                          transition: 'width 0.3s, background-color 0.3s',
                        }}
                      />
                    </div>
                    <span
                      className="text-xs mt-1"
                      style={{ color: pwStrength.color, fontWeight: 600, display: 'block' }}
                    >
                      {pwStrength.label}
                    </span>
                  </div>
                )}
              </div>

              <div className="input-group mb-6">
                <label>Confirm Password</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter your password"
                  required
                  autoComplete="new-password"
                  className={`input ${!passwordsMatch ? 'input-error' : ''}`}
                />
                {!passwordsMatch && (
                  <span className="input-error-msg mt-1 text-xs">
                    Passwords don&apos;t match
                  </span>
                )}
              </div>

              <button
                type="button"
                onClick={() => setStep(1)}
                disabled={!canAdvance()}
                className="btn btn-primary btn-lg w-full"
              >
                Continue
              </button>
            </div>
          )}

          {/* STEP 1: Role Selection */}
          {step === 1 && (
            <div>
              <h2 className="heading-md mb-2">How will you use VetBridge?</h2>
              <p className="text-secondary text-sm mb-6">Choose your role in the community</p>

              <div className="flex-col gap-3 mb-6" style={{ display: 'flex', gap: 12 }}>
                {/* Veteran card */}
                <button
                  type="button"
                  onClick={() => setRole('veteran')}
                  className={`card card-hover ${role === 'veteran' ? 'card-glow' : ''}`}
                  style={{
                    textAlign: 'left',
                    borderColor: role === 'veteran' ? 'var(--accent-primary)' : undefined,
                    boxShadow: role === 'veteran' ? '0 0 20px rgba(129, 140, 248, 0.25)' : undefined,
                  }}
                >
                  <div className="flex-center" style={{ gap: 14, alignItems: 'flex-start' }}>
                    <div
                      className="flex-center"
                      style={{
                        width: 48,
                        height: 48,
                        borderRadius: 12,
                        background: role === 'veteran' ? 'var(--gradient-accent)' : 'var(--bg-glass)',
                        flexShrink: 0,
                      }}
                    >
                      <span style={{ filter: role !== 'veteran' ? 'grayscale(1) opacity(0.5)' : 'none', fontSize: '1.5rem' }}>
                        {'\u2B50'}
                      </span>
                    </div>
                    <div style={{ flex: 1 }}>
                      <div className="heading-sm">I&apos;m a Veteran</div>
                      <div className="text-secondary text-sm mt-1">
                        Get matched with buddies, create check-ins, and send SOS alerts when you need support
                      </div>
                    </div>
                    {role === 'veteran' && (
                      <span className="text-success" style={{ fontSize: '1.2rem', fontWeight: 700, flexShrink: 0 }}>
                        {'\u2713'}
                      </span>
                    )}
                  </div>
                </button>

                {/* Buddy card */}
                <button
                  type="button"
                  onClick={() => setRole('buddy')}
                  className={`card card-hover ${role === 'buddy' ? 'card-glow' : ''}`}
                  style={{
                    textAlign: 'left',
                    borderColor: role === 'buddy' ? 'var(--accent-primary)' : undefined,
                    boxShadow: role === 'buddy' ? '0 0 20px rgba(129, 140, 248, 0.25)' : undefined,
                  }}
                >
                  <div className="flex-center" style={{ gap: 14, alignItems: 'flex-start' }}>
                    <div
                      className="flex-center"
                      style={{
                        width: 48,
                        height: 48,
                        borderRadius: 12,
                        background: role === 'buddy' ? 'var(--gradient-accent)' : 'var(--bg-glass)',
                        flexShrink: 0,
                      }}
                    >
                      <span style={{ filter: role !== 'buddy' ? 'grayscale(1) opacity(0.5)' : 'none', fontSize: '1.5rem' }}>
                        {'\u{1F91D}'}
                      </span>
                    </div>
                    <div style={{ flex: 1 }}>
                      <div className="heading-sm">I&apos;m a Buddy</div>
                      <div className="text-secondary text-sm mt-1">
                        Support veterans by accepting invitations, responding to SOS alerts, and being there
                      </div>
                    </div>
                    {role === 'buddy' && (
                      <span className="text-success" style={{ fontSize: '1.2rem', fontWeight: 700, flexShrink: 0 }}>
                        {'\u2713'}
                      </span>
                    )}
                  </div>
                </button>
              </div>

              <div className="flex-center gap-3" style={{ gap: 10 }}>
                <button type="button" onClick={() => setStep(0)} className="btn btn-secondary" style={{ flex: 1 }}>
                  Back
                </button>
                <button type="button" onClick={() => setStep(2)} className="btn btn-primary btn-lg" style={{ flex: 1 }}>
                  Continue
                </button>
              </div>
            </div>
          )}

          {/* STEP 2: Location */}
          {step === 2 && (
            <div>
              <h2 className="heading-md mb-2">Set your location</h2>
              <p className="text-secondary text-sm mb-6">
                This helps match you with nearby {role === 'veteran' ? 'buddies' : 'veterans'}. You can skip this and set it later.
              </p>

              {/* Address search */}
              <div className="input-group mb-4">
                <label>Search your city, ZIP code, or address</label>
                <div className="relative">
                  <input
                    type="text"
                    value={addressQuery}
                    onChange={(e) => handleAddressSearch(e.target.value)}
                    placeholder="e.g. San Francisco, CA or 10001"
                    className="input"
                    style={selectedAddress ? { borderColor: 'var(--color-success)' } : undefined}
                  />
                  {searchLoading && (
                    <span className="text-muted text-xs absolute" style={{ right: 14, top: '50%', transform: 'translateY(-50%)' }}>
                      Searching...
                    </span>
                  )}
                </div>

                {/* Suggestions dropdown */}
                {suggestions.length > 0 && (
                  <div
                    className="overflow-hidden mt-2"
                    style={{
                      maxHeight: 200,
                      overflowY: 'auto',
                      backgroundColor: 'var(--bg-secondary)',
                      border: '1px solid var(--border-default)',
                      borderRadius: 'var(--radius-md)',
                    }}
                  >
                    {suggestions.map((s, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleSelectSuggestion(s)}
                        className="btn btn-ghost w-full text-left"
                        style={{
                          display: 'block',
                          padding: '10px 14px',
                          borderBottom: idx < suggestions.length - 1 ? '1px solid var(--border-default)' : 'none',
                          borderRadius: 0,
                          fontSize: '0.85rem',
                          color: 'var(--text-primary)',
                        }}
                      >
                        <span style={{ fontWeight: 500 }}>{s.display_name.split(',')[0]}</span>
                        <span className="text-muted text-xs">
                          {s.display_name.includes(',') ? ', ' + s.display_name.split(',').slice(1, 3).join(',').trim() : ''}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Selected location display */}
              {selectedAddress && latitude && longitude && (
                <div
                  className="card card-highlight-success mb-4"
                  style={{
                    backgroundColor: 'var(--color-success-bg)',
                    borderColor: 'var(--color-success-border)',
                  }}
                >
                  <div className="flex-center mb-2" style={{ gap: 8 }}>
                    <span style={{ fontSize: '1.1rem' }}>{'\u2705'}</span>
                    <span className="heading-sm text-success">Location set</span>
                  </div>
                  <p className="text-secondary text-sm" style={{ margin: 0 }}>{selectedAddress}</p>
                  <p className="text-muted text-xs mt-1" style={{ margin: 0 }}>
                    Coordinates: {latitude.toFixed(4)}, {longitude.toFixed(4)}
                  </p>
                </div>
              )}

              {/* Auto-detect divider */}
              <div className="flex-center gap-3 my-4">
                <div className="divider" style={{ margin: 0, flex: 1 }} />
                <span className="text-muted text-xs" style={{ fontWeight: 500 }}>or</span>
                <div className="divider" style={{ margin: 0, flex: 1 }} />
              </div>

              {/* Auto-detect button */}
              <button
                type="button"
                onClick={handleAutoDetect}
                disabled={geoLoading}
                className="btn btn-secondary w-full mb-4"
              >
                <span style={{ fontSize: '1.1rem' }}>{'\uD83D\uDCCD'}</span>
                {geoLoading ? 'Detecting location...' : 'Auto-detect my location'}
              </button>

              {geoError && (
                <div className="alert alert-warning mb-4">
                  <span>{geoError}</span>
                </div>
              )}

              {error && (
                <div className="alert alert-danger mb-4">
                  <span>{error}</span>
                </div>
              )}

              {/* Summary */}
              <div className="card mb-6">
                <div className="heading-sm mb-4">Account Summary</div>
                <div
                  className="text-sm"
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '6px 16px',
                  }}
                >
                  <span className="text-muted">Name</span>
                  <span style={{ color: 'var(--text-primary)' }}>{fullName}</span>
                  <span className="text-muted">Email</span>
                  <span style={{ color: 'var(--text-primary)' }}>{email}</span>
                  <span className="text-muted">Role</span>
                  <span style={{ color: 'var(--text-primary)', textTransform: 'capitalize' }}>{role}</span>
                  <span className="text-muted">Location</span>
                  <span style={{ color: 'var(--text-primary)' }}>{selectedAddress ? selectedAddress.split(',').slice(0, 2).join(', ') : 'Not set (optional)'}</span>
                </div>
              </div>

              <div className="flex-center gap-3" style={{ gap: 10 }}>
                <button type="button" onClick={() => setStep(1)} className="btn btn-secondary" style={{ flex: 1 }}>
                  Back
                </button>
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={loading}
                  className="btn btn-primary btn-lg"
                  style={{ flex: 1 }}
                >
                  {loading ? 'Creating Account...' : 'Create Account'}
                </button>
              </div>
            </div>
          )}

          {/* Footer link */}
          <div className="text-center mt-6 pt-4" style={{ borderTop: '1px solid var(--border-default)' }}>
            <span className="text-secondary text-sm">
              Already have an account?{' '}
              <Link to="/login" className="text-gradient" style={{ fontWeight: 600 }}>
                Sign in
              </Link>
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
