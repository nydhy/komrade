import { useEffect, useState } from 'react'
import { acceptInvite, blockLink, type BuddyLinkWithUser } from '../api/buddies'

interface BuddyListProps {
  links: BuddyLinkWithUser[]
  onUpdated: () => void
}

/** Reverse geocode lat/lng to a human-readable label using Nominatim */
async function reverseGeocode(lat: number, lng: number): Promise<string> {
  try {
    const resp = await fetch(
      `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json&zoom=12`
    )
    if (!resp.ok) return `${lat.toFixed(2)}, ${lng.toFixed(2)}`
    const data = await resp.json()
    const addr = data.address || {}
    const parts = [addr.city || addr.town || addr.village || addr.county, addr.state, addr.country].filter(Boolean)
    return parts.join(', ') || data.display_name || `${lat.toFixed(2)}, ${lng.toFixed(2)}`
  } catch {
    return `${lat.toFixed(2)}, ${lng.toFixed(2)}`
  }
}

const STATUS_BADGE: Record<string, string> = {
  ACCEPTED: 'badge badge-success',
  PENDING: 'badge badge-warning',
  BLOCKED: 'badge badge-danger',
}

const DELAY_CLASSES = [
  '',
  'animate-in-delay-1',
  'animate-in-delay-2',
  'animate-in-delay-3',
  'animate-in-delay-4',
  'animate-in-delay-5',
]

export function BuddyList({ links, onUpdated }: BuddyListProps) {
  const [labels, setLabels] = useState<Record<number, string>>({})

  useEffect(() => {
    const toResolve = links.filter(
      (l) => l.status === 'ACCEPTED' && l.other_latitude != null && l.other_longitude != null && !labels[l.id]
    )
    if (toResolve.length === 0) return
    // Stagger requests slightly to respect Nominatim rate limits
    toResolve.forEach((l, i) => {
      setTimeout(() => {
        reverseGeocode(l.other_latitude!, l.other_longitude!).then((label) =>
          setLabels((prev) => ({ ...prev, [l.id]: label }))
        )
      }, i * 400)
    })
  }, [links])

  async function handleAccept(linkId: number) {
    try {
      await acceptInvite(linkId)
      onUpdated()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Accept failed')
    }
  }

  async function handleBlock(linkId: number) {
    try {
      await blockLink(linkId)
      onUpdated()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Block failed')
    }
  }

  if (links.length === 0) {
    return (
      <div className="card flex-center animate-in" style={{ minHeight: 120 }}>
        <p className="text-muted">No buddy links yet. Send an invite above to get started!</p>
      </div>
    )
  }

  return (
    <div className="flex-col gap-md">
      {links.map((link, idx) => {
        const delayClass = DELAY_CLASSES[Math.min(idx, DELAY_CLASSES.length - 1)]
        const initial = (link.other_name || link.other_email).charAt(0).toUpperCase()

        return (
          <div
            key={link.id}
            className={`card card-hover animate-in ${delayClass}`}
            style={{ padding: '1.1rem 1.35rem' }}
          >
            <div className="flex-between" style={{ alignItems: 'flex-start' }}>
              {/* Left: avatar + info */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'flex-start',
                  gap: '0.85rem',
                  flex: 1,
                  minWidth: 0,
                }}
              >
                <div className="avatar avatar-lg" style={{ background: 'var(--gradient-accent)', flexShrink: 0 }}>
                  {initial}
                </div>

                <div className="flex-col" style={{ gap: '0.32rem', minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-start', gap: '0.5rem' }}>
                    <span className="heading-sm">{link.other_name || 'Unknown'}</span>
                    <span className={STATUS_BADGE[link.status] || 'badge'}>{link.status}</span>
                  </div>

                  <span className="text-secondary text-sm">{link.other_email}</span>

                  <span className="text-xs text-muted">Trust level {link.trust_level}</span>

                  {link.status === 'ACCEPTED' && (
                    <span className="text-xs">
                      {link.other_latitude != null && link.other_longitude != null ? (
                        <span style={{ color: 'var(--accent-primary)' }}>
                          {labels[link.id] || 'Resolving location…'}
                        </span>
                      ) : (
                        <span className="text-muted">Location not set</span>
                      )}
                    </span>
                  )}
                </div>
              </div>

              {/* Right: action buttons */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'flex-end',
                  gap: '0.5rem',
                  marginLeft: '1rem',
                  paddingTop: '0.15rem',
                  flexShrink: 0,
                }}
              >
                {link.status === 'PENDING' && (
                  <button className="btn btn-success btn-sm" onClick={() => handleAccept(link.id)}>
                    Accept
                  </button>
                )}
                {(link.status === 'PENDING' || link.status === 'ACCEPTED') && (
                  <button className="btn btn-danger btn-sm" onClick={() => handleBlock(link.id)}>
                    Block
                  </button>
                )}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
