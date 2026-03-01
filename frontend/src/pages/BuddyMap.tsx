import { useEffect, useState, useRef, useMemo } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet'
import L from 'leaflet'
import { getBuddies } from '../api/buddies'
import { getMe, type UserMe } from '../api/auth'
import { getToken } from '../state/authStore'
import { getMySettings, updateMySettings } from '../api/settings'

// Fix default marker icons for leaflet in bundled apps
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

// @ts-ignore
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

const SOS_RADIUS_KM = 50

// Custom dark-themed icons
const userIcon = new L.DivIcon({
  html: `<div style="background:#6366f1;width:18px;height:18px;border-radius:50%;border:3px solid rgba(255,255,255,0.9);box-shadow:0 0 12px rgba(99,102,241,0.6),0 2px 6px rgba(0,0,0,0.4);"></div>`,
  className: '',
  iconSize: [24, 24],
  iconAnchor: [12, 12],
})

const buddyIcon = new L.DivIcon({
  html: `<div style="background:#10b981;width:14px;height:14px;border-radius:50%;border:2px solid rgba(255,255,255,0.85);box-shadow:0 0 10px rgba(16,185,129,0.5),0 2px 4px rgba(0,0,0,0.35);"></div>`,
  className: '',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
})

const farBuddyIcon = new L.DivIcon({
  html: `<div style="background:#f59e0b;width:14px;height:14px;border-radius:50%;border:2px solid rgba(255,255,255,0.85);box-shadow:0 0 10px rgba(245,158,11,0.5),0 2px 4px rgba(0,0,0,0.35);"></div>`,
  className: '',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
})

function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371
  const dLat = ((lat2 - lat1) * Math.PI) / 180
  const dLon = ((lon2 - lon1) * Math.PI) / 180
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

/** Fit bounds to all markers */
function FitBounds({ positions }: { positions: [number, number][] }) {
  const map = useMap()
  const fitted = useRef(false)
  useEffect(() => {
    if (positions.length > 0 && !fitted.current) {
      const bounds = L.latLngBounds(positions.map(([lat, lng]) => L.latLng(lat, lng)))
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 })
      fitted.current = true
    }
  }, [positions, map])
  return null
}

interface RawBuddyOnMap {
  name: string
  email: string
  lat: number
  lng: number
  distKm: number | null
}

interface BuddyOnMap extends RawBuddyOnMap {
  withinRadius: boolean
}

export default function BuddyMap() {
  const [me, setMe] = useState<UserMe | null>(null)
  const [rawBuddies, setRawBuddies] = useState<RawBuddyOnMap[]>([])
  const [loading, setLoading] = useState(true)
  const [radiusKm, setRadiusKm] = useState(SOS_RADIUS_KM)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [savedRadius, setSavedRadius] = useState(SOS_RADIUS_KM)

  const dirty = radiusKm !== savedRadius

  // Derive buddies with withinRadius from raw data + current radiusKm
  const buddies: BuddyOnMap[] = useMemo(
    () =>
      rawBuddies.map((b) => ({
        ...b,
        withinRadius: b.distKm !== null ? b.distKm <= radiusKm : false,
      })),
    [rawBuddies, radiusKm],
  )

  async function handleSaveRadius() {
    setSaving(true)
    try {
      await updateMySettings({ sos_radius_km: radiusKm })
      setSavedRadius(radiusKm)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch {
      // ignore
    } finally {
      setSaving(false)
    }
  }

  useEffect(() => {
    let mounted = true
    async function load(isInitial = false) {
      try {
        const token = getToken()
        if (!token) return
        if (isInitial) setLoading(true)
        const [meData, links] = await Promise.all([getMe(token), getBuddies()])
        if (!mounted) return
        setMe(meData)

        if (isInitial) {
          try {
            const settings = await getMySettings()
            if (settings.sos_radius_km) {
              setRadiusKm(settings.sos_radius_km)
              setSavedRadius(settings.sos_radius_km)
            }
          } catch { /* ignore */ }
        }

        const accepted = links.filter((l) => l.status === 'ACCEPTED')
        const online = accepted.filter(
          (l) => l.other_presence_status === 'AVAILABLE' || l.other_presence_status === 'BUSY'
        )
        const mapped: RawBuddyOnMap[] = online
          .filter((l) => l.other_latitude != null && l.other_longitude != null)
          .map((l) => {
            const dist =
              meData.latitude && meData.longitude
                ? haversineKm(meData.latitude, meData.longitude, l.other_latitude!, l.other_longitude!)
                : null
            return {
              name: l.other_name || l.other_email,
              email: l.other_email,
              lat: l.other_latitude!,
              lng: l.other_longitude!,
              distKm: dist !== null ? Math.round(dist * 10) / 10 : null,
            }
          })
        setRawBuddies(mapped)
      } catch {
        // ignore
      } finally {
        if (mounted && isInitial) setLoading(false)
      }
    }
    load(true)
    const interval = setInterval(() => load(false), 30000)
    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [])

  if (loading) {
    return (
      <div className="page-container animate-in" style={{ textAlign: 'center' }}>
        <h1 className="heading-lg text-gradient">Find my Komrade</h1>
        <p className="text-muted">Loading map...</p>
      </div>
    )
  }

  const center: [number, number] =
    me?.latitude && me?.longitude ? [me.latitude, me.longitude] : [39.8283, -98.5795]
  const hasUserLocation = !!(me?.latitude && me?.longitude)

  const allPositions: [number, number][] = []
  if (hasUserLocation) allPositions.push(center)
  buddies.forEach((b) => allPositions.push([b.lat, b.lng]))

  const inRadius = buddies.filter((b) => b.withinRadius).length
  const outRadius = buddies.filter((b) => !b.withinRadius).length

  return (
    <div className="page-container animate-in">
      {/* Header + legend */}
      <div className="flex-between" style={{ flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
        <h1 className="heading-lg text-gradient" style={{ margin: 0 }}>Find my Komrade</h1>
        <div className="gap-md" style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', fontSize: '0.85rem' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#6366f1', display: 'inline-block', boxShadow: '0 0 6px rgba(99,102,241,0.5)' }} />
            <span className="text-secondary">You</span>
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#10b981', display: 'inline-block', boxShadow: '0 0 6px rgba(16,185,129,0.5)' }} />
            <span className="text-secondary">In range ({inRadius})</span>
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#f59e0b', display: 'inline-block', boxShadow: '0 0 6px rgba(245,158,11,0.5)' }} />
            <span className="text-secondary">Out of range ({outRadius})</span>
          </span>
        </div>
      </div>

      {/* Radius slider */}
      <div className="card animate-in animate-in-delay-1" style={{ padding: '0.75rem 1rem', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <label className="text-secondary" style={{ fontWeight: 600, fontSize: '0.85rem', whiteSpace: 'nowrap' }}>
            SOS Radius:
          </label>
          <input
            type="range"
            className="slider"
            min={5}
            max={200}
            step={5}
            value={radiusKm}
            onChange={(e) => setRadiusKm(Number(e.target.value))}
            style={{ flex: 1 }}
          />
          <span className="badge badge-info" style={{ minWidth: 60, textAlign: 'center' }}>
            {radiusKm} km
          </span>
          <button
            className={`btn ${dirty ? 'btn-primary' : 'btn-ghost'} btn-sm`}
            disabled={!dirty || saving}
            onClick={handleSaveRadius}
          >
            {saving ? 'Saving...' : saved ? 'Saved!' : 'Submit'}
          </button>
        </div>
        {dirty && (
          <p style={{ margin: '0.5rem 0 0', fontSize: '0.8rem', color: 'var(--color-warning)' }}>
            Unsaved changes — click Submit to apply the new SOS radius.
          </p>
        )}
      </div>

      {/* Location warning */}
      {!hasUserLocation && (
        <div className="alert alert-danger animate-in animate-in-delay-2" style={{ marginBottom: '1rem' }}>
          Your location is not set. Go to <a href="/" style={{ fontWeight: 600, color: 'inherit', textDecoration: 'underline' }}>Dashboard</a> to set it. Showing komrades only.
        </div>
      )}

      {/* Map */}
      <div className="map-container animate-in animate-in-delay-2">
        <MapContainer
          center={center}
          zoom={hasUserLocation ? 10 : 4}
          style={{ height: 500, width: '100%' }}
          scrollWheelZoom={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />

          {allPositions.length > 1 && <FitBounds positions={allPositions} />}

          {/* SOS Vicinity Circle */}
          {hasUserLocation && (
            <Circle
              center={center}
              radius={radiusKm * 1000}
              pathOptions={{
                color: '#6366f1',
                fillColor: '#6366f1',
                fillOpacity: 0.08,
                weight: 2,
                dashArray: '8 4',
              }}
            />
          )}

          {/* User marker */}
          {hasUserLocation && (
            <Marker position={center} icon={userIcon}>
              <Popup>
                <strong>You</strong>
                <br />
                {me?.full_name}
                <br />
                <span style={{ fontSize: '0.8em', color: '#888' }}>SOS range: {radiusKm} km</span>
              </Popup>
            </Marker>
          )}

          {/* Buddy markers */}
          {buddies.map((b, i) => (
            <Marker key={i} position={[b.lat, b.lng]} icon={b.withinRadius ? buddyIcon : farBuddyIcon}>
              <Popup>
                <strong>{b.name}</strong>
                <br />
                <span style={{ fontSize: '0.85em', color: '#888' }}>{b.email}</span>
                {b.distKm !== null && (
                  <>
                    <br />
                    <span style={{ fontSize: '0.85em', color: b.withinRadius ? '#10b981' : '#f59e0b' }}>
                      {b.distKm} km away {b.withinRadius ? '(in SOS range)' : '(outside SOS range)'}
                    </span>
                  </>
                )}
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>

      {/* Buddy table */}
      {buddies.length > 0 && (
        <div className="animate-in animate-in-delay-3" style={{ marginTop: '1.5rem' }}>
          <h3 className="heading-sm" style={{ marginBottom: '0.75rem' }}>
            Komrades
            <span className="badge badge-info" style={{ marginLeft: '0.5rem' }}>{buddies.length}</span>
          </h3>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Distance</th>
                <th>SOS Range</th>
              </tr>
            </thead>
            <tbody>
              {buddies
                .sort((a, b) => (a.distKm ?? 9999) - (b.distKm ?? 9999))
                .map((b, i) => (
                  <tr key={i}>
                    <td>{b.name}</td>
                    <td className="text-muted">{b.email}</td>
                    <td>{b.distKm !== null ? `${b.distKm} km` : 'N/A'}</td>
                    <td>
                      <span className={b.withinRadius ? 'badge badge-success' : 'badge badge-warning'}>
                        {b.withinRadius ? 'In range' : 'Out of range'}
                      </span>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
