import { useEffect, useState } from 'react'
import { updateLocation } from '../api/presence'
import { getMe, updateProfile } from '../api/auth'
import { getToken } from '../state/authStore'
import { searchAddress, type GeocodeSuggestion } from '../api/geocode'

interface LocationUpdateProps {
  onUpdated?: () => void
}

export function LocationUpdate({ onUpdated }: LocationUpdateProps) {
  const [addressQuery, setAddressQuery] = useState('')
  const [suggestions, setSuggestions] = useState<GeocodeSuggestion[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null)
  const [savedCoords, setSavedCoords] = useState<{ lat: number; lng: number } | null>(null)
  const [selectedAddress, setSelectedAddress] = useState('')
  const [saving, setSaving] = useState(false)
  const [geoLoading, setGeoLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [dirty, setDirty] = useState(false)

  // Load saved location on mount
  useEffect(() => {
    async function loadSavedLocation() {
      try {
        const token = getToken()
        if (!token) return
        const me = await getMe(token)
        if (me.latitude && me.longitude) {
          const c = { lat: me.latitude, lng: me.longitude }
          setCoords(c)
          setSavedCoords(c)
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
            } else {
              setSelectedAddress(`${me.latitude.toFixed(4)}, ${me.longitude.toFixed(4)}`)
            }
          } catch {
            setSelectedAddress(`${me.latitude.toFixed(4)}, ${me.longitude.toFixed(4)}`)
          }
        }
      } catch {
        // ignore
      } finally {
        setInitialLoading(false)
      }
    }
    loadSavedLocation()
  }, [])

  async function handleAddressSearch(query: string) {
    setAddressQuery(query)
    setSuccess(false)
    setSelectedAddress('')
    setSearchLoading(true)
    const results = await searchAddress(query)
    setSuggestions(results)
    setSearchLoading(false)
  }

  function handleSelectSuggestion(s: GeocodeSuggestion) {
    setAddressQuery(s.display_name)
    setSelectedAddress(s.display_name)
    setSuggestions([])
    setCoords({ lat: s.lat, lng: s.lon })
    setError(null)
    setSuccess(false)
    setDirty(true)
  }

  async function handleAutoDetect() {
    setGeoLoading(true)
    setError(null)
    setSuccess(false)
    try {
      const res = await fetch('https://ipapi.co/json/')
      if (!res.ok) throw new Error('IP geolocation service unavailable')
      const data = await res.json()
      if (data.latitude && data.longitude) {
        const lat = data.latitude
        const lng = data.longitude
        setCoords({ lat, lng })
        const addr = [data.city, data.region, data.country_name].filter(Boolean).join(', ')
        setSelectedAddress(addr || `${lat.toFixed(4)}, ${lng.toFixed(4)}`)
        setAddressQuery(addr || '')
        setDirty(true)
      } else {
        throw new Error('Could not determine location from IP')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Auto-detect failed. Please type your address above.')
    } finally {
      setGeoLoading(false)
    }
  }

  async function handleSubmit() {
    if (!coords) return
    setSaving(true)
    setError(null)
    try {
      await updateLocation(coords.lat, coords.lng)
      await updateProfile({ latitude: coords.lat, longitude: coords.lng })
      setSavedCoords(coords)
      setSuccess(true)
      setDirty(false)
      onUpdated?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update location')
    } finally {
      setSaving(false)
    }
  }

  if (initialLoading) {
    return (
      <div className="card mb-4">
        <h3 className="heading-sm mb-3">My Location</h3>
        <p className="text-muted text-sm">Loading saved location...</p>
      </div>
    )
  }

  return (
    <div className="card mb-4">
      <h3 className="heading-sm mb-4">My Location</h3>

      {/* Current saved location */}
      {savedCoords && selectedAddress && !success && (
        <div className="location-current-badge mb-4">
          <span className="text-sm">
            {selectedAddress.split(',').slice(0, 3).join(', ')}
          </span>
        </div>
      )}

      {/* Address search */}
      <div className="input-group mb-3 relative">
        <label>Search Address</label>
        <div className="relative">
          <input
            type="text"
            className={`input ${success ? 'location-input-success' : dirty ? 'location-input-dirty' : ''}`}
            value={addressQuery}
            onChange={(e) => handleAddressSearch(e.target.value)}
            placeholder="Type city, ZIP code, or address to update..."
          />
          {searchLoading && (
            <span className="location-search-indicator text-muted text-xs">
              Searching...
            </span>
          )}
        </div>
      </div>

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="location-suggestions-dropdown mb-3">
          {suggestions.map((s, idx) => (
            <button
              key={idx}
              type="button"
              className="location-suggestion-item"
              onClick={() => handleSelectSuggestion(s)}
            >
              <span className="location-suggestion-primary">
                {s.display_name.split(',')[0]}
              </span>
              <span className="text-muted text-xs">
                {s.display_name.includes(',') ? ', ' + s.display_name.split(',').slice(1, 3).join(',').trim() : ''}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Actions row */}
      <div className="flex-between gap-sm mb-3" style={{ flexWrap: 'wrap' }}>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={handleAutoDetect}
          disabled={geoLoading}
        >
          <span>{'\uD83D\uDCCD'}</span>
          {geoLoading ? 'Detecting...' : 'Auto-detect'}
        </button>

        <button
          type="button"
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={!dirty || saving || !coords}
        >
          {saving ? 'Saving...' : 'Save Location'}
        </button>
      </div>

      {/* Status messages */}
      {dirty && coords && (
        <p className="text-warning text-sm mt-2">
          Unsaved changes &mdash; click "Save Location" to confirm.
        </p>
      )}
      {success && coords && (
        <p className="text-success text-sm mt-2">
          Location saved: {selectedAddress ? selectedAddress.split(',').slice(0, 2).join(', ') : `${coords.lat.toFixed(4)}, ${coords.lng.toFixed(4)}`}
        </p>
      )}
      {error && <p className="text-danger text-sm mt-2">{error}</p>}
    </div>
  )
}
