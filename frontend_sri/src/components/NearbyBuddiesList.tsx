import { useEffect, useState } from 'react'
import { getNearbyBuddies, type NearbyBuddy } from '../api/presence'

function getStatusDotClass(status: string): string {
  switch (status) {
    case 'AVAILABLE': return 'status-dot-available'
    case 'BUSY': return 'status-dot-busy'
    default: return 'status-dot-offline'
  }
}

function getStatusBadgeClass(status: string): string {
  switch (status) {
    case 'AVAILABLE': return 'badge-success'
    case 'BUSY': return 'badge-warning'
    default: return ''
  }
}

export function NearbyBuddiesList() {
  const [buddies, setBuddies] = useState<NearbyBuddy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setError(null)
    setLoading(true)
    try {
      const data = await getNearbyBuddies(10)
      setBuddies(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load nearby buddies')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  if (loading) {
    return <p className="text-secondary text-sm">Loading nearby buddies...</p>
  }
  if (error) {
    return <div className="alert alert-danger text-sm">{error}</div>
  }
  if (buddies.length === 0) {
    return <p className="text-muted text-sm">No accepted buddies found.</p>
  }

  return (
    <div>
      <div className="flex-between mb-4">
        <span className="text-muted text-xs">
          Ranked by availability, trust, and distance
        </span>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={load}
        >
          Refresh
        </button>
      </div>

      <div className="flex-col gap-sm">
        {buddies.map((b, idx) => (
          <div key={b.buddy_id} className="card card-hover buddy-card">
            <div className="buddy-card-inner">
              <span className="buddy-rank text-muted">#{idx + 1}</span>
              <span className={`status-dot ${getStatusDotClass(b.presence_status)}`} />
              <div className="buddy-info">
                <span className="buddy-name">{b.buddy_name}</span>
                <span className="text-muted text-xs">
                  {b.buddy_email} &middot; trust {b.trust_level}/5
                </span>
              </div>
              <div className="buddy-meta">
                <span className={`badge badge-sm ${getStatusBadgeClass(b.presence_status)}`}>
                  {b.presence_status}
                </span>
                {b.distance_km !== null && (
                  <span className="text-muted text-xs">
                    {b.distance_km < 1 ? '<1' : Math.round(b.distance_km)} km
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
