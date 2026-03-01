import { useEffect, useState } from 'react'
import { updateLocation } from '../api/presence'
import { getMeFresh } from '../api/auth'
import { getToken } from '../state/authStore'
import { searchAddress, type GeocodeSuggestion } from '../api/geocode'

/* ── localStorage helpers ── */
const STORAGE_KEY = 'vetbridge_location'

interface CachedLocation {
  lat: number
  lng: number
  address: string
}

function getCachedLocation(): CachedLocation | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed.lat === 'number' && typeof parsed.lng === 'number' && parsed.address) {
      return parsed as CachedLocation
    }
  } catch { /* ignore corrupt data */ }
  return null
}

function setCachedLocation(loc: CachedLocation) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(loc))
  } catch { /* quota exceeded – ignore */ }
}

/** Coordinates are "close enough" (within ~11 metres). */
function coordsMatch(a: { lat: number; lng: number }, b: { lat: number; lng: number }) {
  return Math.abs(a.lat - b.lat) < 0.0001 && Math.abs(a.lng - b.lng) < 0.0001
}

/* ── Geolocation helpers ── */

/**
 * Race low-accuracy (WiFi / cell – fast) against high-accuracy
 * (GPS – slower but more precise) browser geolocation.  The first
 * one to succeed wins.  If *both* fail, the returned promise rejects
 * with the most actionable error (PERMISSION_DENIED > others).
 */
function raceBrowserLocations(): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    let resolved = false
    const errors: GeolocationPositionError[] = []
    const TOTAL = 2

    function onSuccess(pos: GeolocationPosition) {
      if (resolved) return
      resolved = true
      resolve(pos)
    }

    function onError(err: GeolocationPositionError) {
      if (resolved) return
      errors.push(err)
      if (errors.length >= TOTAL) {
        // Prefer PERMISSION_DENIED since it's actionable for the user
        const denied = errors.find((e) => e.code === e.PERMISSION_DENIED)
        reject(denied ?? errors[0])
      }
    }

    // Low-accuracy: WiFi / cell triangulation – usually responds fast
    navigator.geolocation.getCurrentPosition(onSuccess, onError, {
      enableHighAccuracy: false,
      timeout: 10_000,
      maximumAge: 300_000,
    })

    // High-accuracy: GPS – takes longer but gives precise coordinates
    navigator.geolocation.getCurrentPosition(onSuccess, onError, {
      enableHighAccuracy: true,
      timeout: 25_000,
      maximumAge: 300_000,
    })
  })
}

/** IP-based geolocation (last-resort fallback, city-level accuracy). */
async function getIPLocation(): Promise<{ lat: number; lng: number; address: string }> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 8_000)
  try {
    const res = await fetch('https://ipapi.co/json/', { signal: controller.signal })
    if (!res.ok) throw new Error('IP geolocation request failed')
    const data = await res.json()
    if (typeof data.latitude === 'number' && typeof data.longitude === 'number') {
      const addr = [data.city, data.region, data.country_name].filter(Boolean).join(', ')
      return { lat: data.latitude, lng: data.longitude, address: addr }
    }
    throw new Error('No coordinates in IP response')
  } finally {
    clearTimeout(timer)
  }
}

/**
 * Multi-strategy location detection:
 *
 * 1. Race a low-accuracy (WiFi / cell) request against a high-accuracy
 *    (GPS) request.  Whichever resolves first wins.
 * 2. If the browser Geolocation API fails entirely (permission denied
 *    is surfaced directly), fall back to IP-based geolocation.
 */
async function detectLocation(): Promise<{
  lat: number
  lng: number
  address?: string
  approximate?: boolean
}> {
  // If browser geolocation is available, try it first
  if (navigator.geolocation) {
    try {
      const pos = await raceBrowserLocations()
      return { lat: pos.coords.latitude, lng: pos.coords.longitude }
    } catch (geoErr) {
      // If permission was denied, tell the user immediately
      if (
        geoErr instanceof GeolocationPositionError &&
        geoErr.code === geoErr.PERMISSION_DENIED
      ) {
        throw new Error(
          'Location permission denied. Please allow location access in your browser settings, or type your address above.',
        )
      }
      // Timeout / position-unavailable → fall through to IP fallback
    }
  }

  // Fallback: IP-based geolocation
  try {
    const ip = await getIPLocation()
    return { ...ip, approximate: true }
  } catch {
    throw new Error(
      'Could not detect your location. Please type your address above.',
    )
  }
}

/* ── Component ── */
interface LocationUpdateProps {
  onUpdated?: () => void
}

export function LocationUpdate({ onUpdated }: LocationUpdateProps) {
  // Read cache ONCE on mount via lazy initializer (never re-read on re-renders)
  const [cached] = useState(() => getCachedLocation())

  const [addressQuery, setAddressQuery] = useState(cached?.address ?? '')
  const [suggestions, setSuggestions] = useState<GeocodeSuggestion[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(
    cached ? { lat: cached.lat, lng: cached.lng } : null
  )
  const [savedCoords, setSavedCoords] = useState<{ lat: number; lng: number } | null>(
    cached ? { lat: cached.lat, lng: cached.lng } : null
  )
  const [selectedAddress, setSelectedAddress] = useState(cached?.address ?? '')
  const [saving, setSaving] = useState(false)
  const [geoLoading, setGeoLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  // If we already have cached data, skip the loading state entirely
  const [initialLoading, setInitialLoading] = useState(!cached)

  // On mount: verify against the server in the background.
  // If the server coords match the cache → do nothing (instant display already correct).
  // If different → update display.
  useEffect(() => {
    let cancelled = false

    async function verifyFromServer() {
      try {
        const token = getToken()
        if (!token) return

        const me = await getMeFresh(token)

        if (cancelled) return

        if (me.latitude != null && me.longitude != null) {
          const serverCoords = { lat: me.latitude, lng: me.longitude }

          // If cache already matches server, nothing to do
          if (cached && coordsMatch(cached, serverCoords)) {
            return
          }

          // Server has different coords (or no cache) → update display
          setCoords(serverCoords)
          setSavedCoords(serverCoords)

          // Try to reverse-geocode to get a friendly address
          try {
            const res = await fetch(
              `https://nominatim.openstreetmap.org/reverse?lat=${me.latitude}&lon=${me.longitude}&format=json`,
              { headers: { 'Accept-Language': 'en' } }
            )
            if (cancelled) return
            if (res.ok) {
              const data = await res.json()
              const addr = data.display_name || `${me.latitude.toFixed(4)}, ${me.longitude.toFixed(4)}`
              setSelectedAddress(addr)
              setAddressQuery(addr)
              setCachedLocation({ lat: me.latitude, lng: me.longitude, address: addr })
            } else {
              const fallback = `${me.latitude.toFixed(4)}, ${me.longitude.toFixed(4)}`
              setSelectedAddress(fallback)
              setAddressQuery(fallback)
              setCachedLocation({ lat: me.latitude, lng: me.longitude, address: fallback })
            }
          } catch {
            if (cancelled) return
            const fallback = `${me.latitude.toFixed(4)}, ${me.longitude.toFixed(4)}`
            setSelectedAddress(fallback)
            setAddressQuery(fallback)
            setCachedLocation({ lat: me.latitude, lng: me.longitude, address: fallback })
          }
        }
      } catch {
        // network error – keep showing cached data
      } finally {
        if (!cancelled) setInitialLoading(false)
      }
    }

    verifyFromServer()
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleAddressSearch(query: string) {
    setAddressQuery(query)
    setSuccess(false)
    setNotice(null)
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
    setNotice(null)
    setSuccess(false)
    setDirty(true)
  }

  async function handleAutoDetect() {
    setGeoLoading(true)
    setError(null)
    setNotice(null)
    setSuccess(false)

    try {
      const location = await detectLocation()
      const { lat, lng } = location
      setCoords({ lat, lng })

      // If IP fallback provided a city-level address, use it directly.
      // Otherwise reverse-geocode for a street-level address.
      if (location.address) {
        setSelectedAddress(location.address)
        setAddressQuery(location.address)
      } else {
        // Reverse-geocode to get a readable address
        try {
          const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`,
            { headers: { 'Accept-Language': 'en' } }
          )
          if (res.ok) {
            const data = await res.json()
            const addr = data.display_name || `${lat.toFixed(4)}, ${lng.toFixed(4)}`
            setSelectedAddress(addr)
            setAddressQuery(addr)
          } else {
            setSelectedAddress(`${lat.toFixed(4)}, ${lng.toFixed(4)}`)
            setAddressQuery(`${lat.toFixed(4)}, ${lng.toFixed(4)}`)
          }
        } catch {
          setSelectedAddress(`${lat.toFixed(4)}, ${lng.toFixed(4)}`)
          setAddressQuery(`${lat.toFixed(4)}, ${lng.toFixed(4)}`)
        }
      }

      setDirty(true)

      // If we fell back to IP geolocation, inform the user
      if (location.approximate) {
        setNotice(
          'Location detected approximately via your network. You can refine it using the address search above.',
        )
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
    setNotice(null)
    try {
      await updateLocation(coords.lat, coords.lng)
      setSavedCoords(coords)
      setSuccess(true)
      setDirty(false)
      // Persist to localStorage so the address survives navigation
      setCachedLocation({ lat: coords.lat, lng: coords.lng, address: selectedAddress })
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
      {notice && <p className="text-muted text-sm mt-2" style={{ color: '#b8860b' }}>{notice}</p>}
      {error && <p className="text-danger text-sm mt-2">{error}</p>}
    </div>
  )
}
