import { useEffect, useState } from 'react'
import { getIncomingAlerts, type IncomingSosAlert } from '../api/sos'
import { SOSAlertCard } from '../components/SOSAlertCard'
import { useRealtime } from '../state/realtime'

export default function BuddyInbox() {
  const [alerts, setAlerts] = useState<IncomingSosAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setError(null)
    setLoading(true)
    try {
      const data = await getIncomingAlerts()
      setAlerts(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load inbox')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  // Realtime: refresh when new SOS arrives or existing one is closed
  useRealtime(['sos.created', 'sos.closed'], () => {
    load()
  })

  const openAlerts = alerts.filter((a) => a.alert_status !== 'CLOSED')
  const closedAlerts = alerts.filter((a) => a.alert_status === 'CLOSED')

  return (
    <div className="page-container animate-in">
      {/* Header */}
      <div className="flex-between" style={{ marginBottom: '1.5rem' }}>
        <h1 className="heading-lg">Buddy Inbox</h1>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={load}
          disabled={loading}
        >
          {loading ? 'Refreshing...' : '↻ Refresh'}
        </button>
      </div>

      {/* Error alert */}
      {error && (
        <div className="alert alert-danger animate-in" style={{ marginBottom: '1rem' }}>
          <p style={{ margin: 0 }}>{error}</p>
        </div>
      )}

      {/* Loading state */}
      {loading && alerts.length === 0 && (
        <div className="card animate-in" style={{ textAlign: 'center', padding: '2rem' }}>
          <p className="text-muted">Loading incoming alerts...</p>
        </div>
      )}

      {/* Empty state */}
      {!loading && alerts.length === 0 && (
        <div className="card animate-in" style={{ textAlign: 'center', padding: '3rem 1.5rem' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem', opacity: 0.5 }}>📭</div>
          <p className="heading-sm" style={{ marginBottom: '0.25rem' }}>No incoming SOS alerts</p>
          <p className="text-muted">
            When a veteran you're connected with sends an SOS, it will appear here.
          </p>
        </div>
      )}

      {/* Open / active alerts */}
      {openAlerts.length > 0 && (
        <section style={{ marginBottom: '2rem' }}>
          <h2 className="heading-sm" style={{ marginBottom: '0.75rem' }}>
            Active Alerts
            <span className="badge badge-danger" style={{ marginLeft: '0.5rem' }}>
              {openAlerts.length}
            </span>
          </h2>
          {openAlerts.map((a, i) => (
            <div key={`${a.alert_id}-${a.recipient_id}`} className={`animate-in animate-in-delay-${Math.min(i + 1, 5)}`}>
              <SOSAlertCard alert={a} onResponded={load} />
            </div>
          ))}
        </section>
      )}

      {/* Closed alerts */}
      {closedAlerts.length > 0 && (
        <section>
          <div className="divider" />
          <h2 className="heading-sm text-muted" style={{ marginBottom: '0.75rem' }}>
            Closed
            <span className="badge" style={{ marginLeft: '0.5rem' }}>
              {closedAlerts.length}
            </span>
          </h2>
          {closedAlerts.map((a, i) => (
            <div key={`${a.alert_id}-${a.recipient_id}`} className={`animate-in animate-in-delay-${Math.min(i + 1, 5)}`} style={{ opacity: 0.6 }}>
              <SOSAlertCard alert={a} onResponded={load} />
            </div>
          ))}
        </section>
      )}
    </div>
  )
}
