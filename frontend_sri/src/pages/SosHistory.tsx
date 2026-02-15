import { useEffect, useState } from 'react'
import { closeSos, deleteSos, getMySos, type SosAlert, type SosRecipient } from '../api/sos'
import { useRealtime } from '../state/realtime'

function severityClass(severity: string) {
  switch (severity) {
    case 'HIGH': return 'severity-high'
    case 'MED': return 'severity-med'
    case 'LOW': return 'severity-low'
    default: return ''
  }
}

function RecipientResponses({ recipients }: { recipients: SosRecipient[] }) {
  return (
    <div className="mt-3">
      <span className="text-secondary text-sm">Recipients:</span>
      <ul className="mt-1 flex-col gap-xs" style={{ listStyle: 'none', paddingLeft: 0 }}>
        {recipients.map((r) => (
          <li key={r.id} className="text-sm">
            <span className="text-secondary">• {r.buddy_name}</span>
            <span className="text-muted"> — {r.status}</span>
            {(r.status === 'ACCEPTED' || r.status === 'DECLINED') ? (
              <div className="text-muted text-xs mt-1" style={{ paddingLeft: '1rem' }}>
                {r.message ? `"${r.message}"` : '(no message)'}
                {r.status === 'ACCEPTED' && r.eta_minutes != null && (
                  <> · ETA: {r.eta_minutes} min</>
                )}
                {r.responded_at && (
                  <> · {new Date(r.responded_at).toLocaleString()}</>
                )}
              </div>
            ) : (
              <div className="text-muted text-xs mt-1" style={{ paddingLeft: '1rem' }}>
                (no response yet)
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function SosHistory() {
  const [alerts, setAlerts] = useState<SosAlert[]>([])
  const [loading, setLoading] = useState(true)

  async function load() {
    try {
      const data = await getMySos(50)
      setAlerts(data)
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  useRealtime(['sos.recipient_updated', 'sos.closed'], () => {
    getMySos(50).then(setAlerts).catch(() => {})
  })

  async function handleClose(sosId: number) {
    try {
      const updated = await closeSos(sosId)
      setAlerts((prev) => prev.map((a) => (a.id === sosId ? updated : a)))
    } catch { /* ignore */ }
  }

  async function handleDelete(sosId: number) {
    if (!confirm('Delete this SOS alert and all its notifications? This cannot be undone.')) return
    try {
      await deleteSos(sosId)
      setAlerts((prev) => prev.filter((a) => a.id !== sosId))
    } catch { /* ignore */ }
  }

  if (loading) {
    return (
      <div className="page-container animate-in">
        <h1 className="heading-lg text-gradient">SOS History</h1>
        <div className="card loading-shimmer skeleton-card mt-6" />
      </div>
    )
  }

  const open = alerts.filter((a) => a.status !== 'CLOSED')
  const closed = alerts.filter((a) => a.status === 'CLOSED')

  return (
    <div className="page-container animate-in">
      <h1 className="heading-lg text-gradient mb-6">SOS History</h1>

      {alerts.length === 0 ? (
        <div className="card">
          <p className="text-muted text-sm text-center">No SOS alerts yet.</p>
        </div>
      ) : (
        <>
          {open.length > 0 && (
            <section className="mb-6">
              <h2 className="heading-md mb-4">Active Alerts</h2>
              <div className="flex-col gap-md">
                {open.map((alert, idx) => (
                  <div
                    key={alert.id}
                    className={`card ${severityClass(alert.severity)} sos-pulse animate-in animate-in-delay-${Math.min(idx, 4)}`}
                  >
                    <div className="flex-between">
                      <div className="flex-center gap-sm">
                        <span className="status-dot status-dot-danger" />
                        <strong className="heading-sm">
                          SOS #{alert.id} — {alert.trigger_type} / {alert.severity}
                        </strong>
                        <span className="badge badge-danger">{alert.status}</span>
                      </div>
                      <div className="flex-center gap-sm">
                        <button
                          type="button"
                          onClick={() => handleClose(alert.id)}
                          className="btn btn-ghost btn-sm"
                        >
                          Close
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(alert.id)}
                          className="btn btn-danger btn-sm"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                    <RecipientResponses recipients={alert.recipients} />
                    <p className="text-muted text-xs mt-1">
                      Created: {new Date(alert.created_at).toLocaleString()}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {closed.length > 0 && (
            <section>
              <h2 className="heading-md mb-4">Closed Alerts</h2>
              <div className="flex-col gap-md">
                {closed.map((alert, idx) => (
                  <div
                    key={alert.id}
                    className={`card ${severityClass(alert.severity)} animate-in animate-in-delay-${Math.min(idx, 4)}`}
                  >
                    <div className="flex-between">
                      <div className="flex-center gap-sm">
                        <span className="status-dot status-dot-offline" />
                        <strong className="heading-sm">
                          SOS #{alert.id} — {alert.trigger_type} / {alert.severity}
                        </strong>
                        <span className="badge">{alert.status}</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleDelete(alert.id)}
                        className="btn btn-danger btn-sm"
                      >
                        Delete
                      </button>
                    </div>
                    <RecipientResponses recipients={alert.recipients} />
                    <p className="text-muted text-xs mt-1">
                      Created: {new Date(alert.created_at).toLocaleString()}
                      {alert.closed_at && ` · Closed: ${new Date(alert.closed_at).toLocaleString()}`}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  )
}
