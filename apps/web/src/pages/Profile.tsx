import { useEffect, useState } from 'react'
import { getMe, updateProfile, type UserMe } from '../api/auth'
import { getToken } from '../state/authStore'
import { searchAddress, type GeocodeSuggestion } from '../api/geocode'

export default function Profile() {
  const [user, setUser] = useState<UserMe | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  // Editable fields
  const [fullName, setFullName] = useState('')
  const [addressQuery, setAddressQuery] = useState('')
  const [selectedAddress, setSelectedAddress] = useState('')
  const [latitude, setLatitude] = useState<number | null>(null)
  const [longitude, setLongitude] = useState<number | null>(null)
  const [suggestions, setSuggestions] = useState<GeocodeSuggestion[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [geoLoading, setGeoLoading] = useState(false)

  useEffect(() => {
    async function load() {
      try {
        const token = getToken()
        if (!token) return
        const me = await getMe(token)
        setUser(me)
        setFullName(me.full_name)
        setLatitude(me.latitude)
        setLongitude(me.longitude)
        // Reverse-geocode saved location
        if (me.latitude && me.longitude) {
          try {
            const res = await fetch(
              `https://nominatim.openstreetmap.org/reverse?lat=${me.latitude}&lon=${me.longitude}&format=json`,
              { headers: { 'Accept-Language': 'en' } }
            )
            if (res.ok) {
              const data = await res.json()
              const addr = data.display_name || `${me.latitude.toFixed(4)}, ${me.longitude.toFixed(4)}`
              setSelectedAddress(addr)
              setAddressQuery(addr)
            }
          } catch {
            setSelectedAddress(`${me.latitude.toFixed(4)}, ${me.longitude.toFixed(4)}`)
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load profile')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  async function handleAddressSearch(query: string) {
    setAddressQuery(query)
    setSelectedAddress('')
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
    setError(null)
    try {
      const res = await fetch('https://ipapi.co/json/')
      if (!res.ok) throw new Error('IP geolocation unavailable')
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
      setError(err instanceof Error ? err.message : 'Auto-detect failed')
    } finally {
      setGeoLoading(false)
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSuccess(false)
    try {
      const updated = await updateProfile({
        full_name: fullName || undefined,
        latitude: latitude ?? undefined,
        longitude: longitude ?? undefined,
      })
      setUser(updated)
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save profile')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="page-container flex-center" style={{ minHeight: '40vh' }}>
        <p className="text-secondary">Loading profile...</p>
      </div>
    )
  }

  return (
    <div className="page-container page-container-narrow">
      <div className="animate-in mb-8">
        <h1 className="heading-lg mb-2">My Profile</h1>
        <p className="text-muted">Update your personal information and location</p>
      </div>

      {error && (
        <div className="alert alert-danger animate-in mb-4">
          {error}
        </div>
      )}
      {success && (
        <div className="alert alert-success animate-in mb-4">
          Profile saved successfully.
        </div>
      )}

      <form onSubmit={handleSave} className="flex-col gap-lg">
        {/* Account info (read-only) */}
        <section className="card animate-in animate-in-delay-1">
          <h2 className="heading-md mb-4">Account</h2>
          <div className="divider mb-4" />
          <div className="profile-info-grid">
            <span className="text-secondary text-sm">Email</span>
            <span className="text-sm">{user?.email}</span>
            <span className="text-secondary text-sm">Role</span>
            <span className="text-sm" style={{ textTransform: 'capitalize' }}>{user?.role}</span>
            <span className="text-secondary text-sm">Joined</span>
            <span className="text-sm">{user?.created_at ? new Date(user.created_at).toLocaleDateString() : ''}</span>
          </div>
        </section>

        {/* Editable name */}
        <section className="card animate-in animate-in-delay-2">
          <h2 className="heading-md mb-4">Personal Info</h2>
          <div className="divider mb-4" />
          <div className="input-group">
            <label>Full Name</label>
            <input
              type="text"
              className="input"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Your full name"
            />
          </div>
        </section>

        {/* Location */}
        <section className="card animate-in animate-in-delay-3">
          <h2 className="heading-md mb-2">Location</h2>
          <p className="text-muted text-sm mb-4">
            Used for matching you with nearby {user?.role === 'veteran' ? 'buddies' : 'veterans'}
          </p>
          <div className="divider mb-4" />

          {/* Current location badge */}
          {latitude && longitude && selectedAddress && (
            <div className="badge badge-info mb-4" style={{ fontSize: 'var(--text-sm)', padding: '8px 14px' }}>
              Current: {selectedAddress.split(',').slice(0, 3).join(', ')}
            </div>
          )}

          {/* Address search */}
          <div className="input-group mb-3 relative">
            <label>Search Address</label>
            <div className="relative">
              <input
                type="text"
                className={`input ${selectedAddress ? 'input-success' : ''}`}
                value={addressQuery}
                onChange={(e) => handleAddressSearch(e.target.value)}
                placeholder="Search city, ZIP code, or address..."
              />
              {searchLoading && (
                <span className="profile-search-indicator text-muted text-xs">
                  Searching...
                </span>
              )}
            </div>
          </div>

          {/* Suggestions dropdown */}
          {suggestions.length > 0 && (
            <div className="profile-suggestions-dropdown mb-3">
              {suggestions.map((s, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="profile-suggestion-item"
                  onClick={() => handleSelectSuggestion(s)}
                >
                  <span className="profile-suggestion-primary">
                    {s.display_name.split(',')[0]}
                  </span>
                  <span className="text-muted text-xs">
                    {s.display_name.includes(',') ? ', ' + s.display_name.split(',').slice(1, 3).join(',').trim() : ''}
                  </span>
                </button>
              ))}
            </div>
          )}

          {/* Auto-detect */}
          <button
            type="button"
            className="btn btn-ghost"
            onClick={handleAutoDetect}
            disabled={geoLoading}
          >
            <span>{'\uD83D\uDCCD'}</span>
            {geoLoading ? 'Detecting...' : 'Auto-detect my location'}
          </button>
        </section>

        {/* Save button */}
        <div className="animate-in animate-in-delay-4">
          <button
            type="submit"
            className="btn btn-primary btn-lg w-full"
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Profile'}
          </button>
        </div>
      </form>
    </div>
  )
}
