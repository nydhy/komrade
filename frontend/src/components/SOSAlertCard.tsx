import { useState } from 'react'
import { respondToSos, type IncomingSosAlert } from '../api/sos'

interface SOSAlertCardProps {
  alert: IncomingSosAlert
  onResponded: () => void
}

const SEVERITY_CLASS: Record<string, string> = {
  HIGH: 'severity-high',
  MED: 'severity-med',
  LOW: 'severity-low',
}

const SEVERITY_BADGE: Record<string, string> = {
  HIGH: 'badge badge-danger',
  MED: 'badge badge-warning',
  LOW: 'badge badge-success',
}

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  NOTIFIED: { label: 'Pending', className: 'badge badge-warning' },
  ACCEPTED: { label: 'Accepted', className: 'badge badge-success' },
  DECLINED: { label: 'Declined', className: 'badge badge-danger' },
  NO_RESPONSE: { label: 'No Response', className: 'badge' },
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function SOSAlertCard({ alert, onResponded }: SOSAlertCardProps) {
  const [message, setMessage] = useState('')
  const [eta, setEta] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)

  const statusBadge = STATUS_BADGE[alert.my_status] ?? STATUS_BADGE.NO_RESPONSE
  const sevClass = SEVERITY_CLASS[alert.severity] ?? ''
  const sevBadgeClass = SEVERITY_BADGE[alert.severity] ?? 'badge'
  const isClosed = alert.alert_status === 'CLOSED'
  const hasResponded = alert.my_status === 'ACCEPTED' || alert.my_status === 'DECLINED'

  async function handleRespond(status: 'ACCEPTED' | 'DECLINED') {
    setLoading(true)
    setError(null)
    try {
      const etaNum = eta ? parseInt(eta, 10) : undefined
      if (etaNum !== undefined && (etaNum < 1 || etaNum > 120)) {
        setError('ETA must be between 1 and 120 minutes')
        setLoading(false)
        return
      }
      await respondToSos(alert.alert_id, {
        status,
        message: message || undefined,
        eta_minutes: status === 'ACCEPTED' ? etaNum : undefined,
      })
      onResponded()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to respond')
    } finally {
      setLoading(false)
    }
  }

  const cardClasses = [
    'card',
    'card-hover',
    sevClass,
    isClosed ? '' : 'card-glow',
    alert.severity === 'HIGH' && !isClosed ? 'card-highlight-danger' : '',
    alert.severity === 'MED' && !isClosed ? 'card-highlight-warning' : '',
    alert.severity === 'LOW' && !isClosed ? 'card-highlight-success' : '',
    'animate-in',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={cardClasses} style={{ marginBottom: '0.75rem' }}>
      {/* Header row */}
      <div className="flex-between" style={{ flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span className="heading-sm" style={{ margin: 0 }}>
            SOS from {alert.veteran_name}
          </span>
          <span className={sevBadgeClass}>{alert.severity}</span>
          <span className="badge badge-info">{alert.trigger_type}</span>
        </div>
        <span className={statusBadge.className}>{statusBadge.label}</span>
      </div>

      {/* Date */}
      <div className="text-muted" style={{ fontSize: '0.85rem', marginBottom: '0.5rem' }}>
        {formatDate(alert.created_at)}
        {isClosed && <span style={{ marginLeft: '0.5rem' }}>(Closed)</span>}
      </div>

      {/* Already responded info */}
      {hasResponded && (
        <div className="card" style={{ padding: '0.5rem 0.75rem', marginBottom: '0.5rem' }}>
          {alert.my_status === 'ACCEPTED' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <span className="badge badge-success">✓ You accepted</span>
              {alert.my_eta_minutes && (
                <span className="text-secondary" style={{ fontSize: '0.85rem' }}>
                  ETA: {alert.my_eta_minutes} min
                </span>
              )}
            </div>
          )}
          {alert.my_status === 'DECLINED' && (
            <span className="badge badge-danger">✗ You declined</span>
          )}
          {alert.my_message && (
            <div className="text-muted" style={{ marginTop: '0.35rem', fontStyle: 'italic', fontSize: '0.85rem' }}>
              "{alert.my_message}"
            </div>
          )}
        </div>
      )}

      {/* Action buttons / response form */}
      {!isClosed && (
        <div style={{ marginTop: '0.5rem' }}>
          {!showForm ? (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => setShowForm(true)}
            >
              {hasResponded ? 'Change Response' : 'Respond'}
            </button>
          ) : (
            <div className="form-section">
              {/* Message input */}
              <div style={{ marginBottom: '0.75rem' }}>
                <label className="text-secondary" style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.35rem', fontWeight: 500 }}>
                  Message (optional)
                </label>
                <input
                  type="text"
                  className="input"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="e.g. On my way!"
                />
              </div>

              {/* ETA input */}
              <div style={{ marginBottom: '0.75rem' }}>
                <label className="text-secondary" style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.35rem', fontWeight: 500 }}>
                  ETA in minutes (1–120, optional)
                </label>
                <input
                  type="number"
                  className="input"
                  value={eta}
                  onChange={(e) => setEta(e.target.value)}
                  placeholder="e.g. 15"
                  min={1}
                  max={120}
                  style={{ maxWidth: 140 }}
                />
              </div>

              {/* Error */}
              {error && (
                <div className="alert alert-danger" style={{ marginBottom: '0.75rem', padding: '0.5rem 0.75rem', fontSize: '0.85rem' }}>
                  {error}
                </div>
              )}

              {/* Action buttons */}
              <div className="gap-sm" style={{ display: 'flex' }}>
                <button
                  type="button"
                  className="btn btn-success btn-sm"
                  onClick={() => handleRespond('ACCEPTED')}
                  disabled={loading}
                >
                  Accept
                </button>
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  onClick={() => handleRespond('DECLINED')}
                  disabled={loading}
                >
                  Decline
                </button>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => { setShowForm(false); setError(null) }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
