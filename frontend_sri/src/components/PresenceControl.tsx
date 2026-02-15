import { useEffect, useState } from 'react'
import { getMyPresence, updatePresence, type PresenceStatus } from '../api/presence'

interface PresenceControlProps {
  initialStatus?: PresenceStatus
  onUpdated?: (newStatus: PresenceStatus) => void
}

const STATUS_OPTIONS: {
  value: PresenceStatus
  label: string
  dotClass: string
  activeClass: string
}[] = [
  {
    value: 'AVAILABLE',
    label: 'Available',
    dotClass: 'status-dot-available',
    activeClass: 'presence-btn-available-active',
  },
  {
    value: 'BUSY',
    label: 'Busy',
    dotClass: 'status-dot-busy',
    activeClass: 'presence-btn-busy-active',
  },
  {
    value: 'OFFLINE',
    label: 'Offline',
    dotClass: 'status-dot-offline',
    activeClass: 'presence-btn-offline-active',
  },
]

export function PresenceControl({ onUpdated }: PresenceControlProps) {
  const [savedStatus, setSavedStatus] = useState<PresenceStatus>('OFFLINE')
  const [selectedStatus, setSelectedStatus] = useState<PresenceStatus>('OFFLINE')
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const dirty = selectedStatus !== savedStatus

  useEffect(() => {
    getMyPresence()
      .then((p) => {
        const s = p.status as PresenceStatus
        setSavedStatus(s)
        setSelectedStatus(s)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  async function handleSubmit() {
    setSaving(true)
    setError(null)
    try {
      await updatePresence(selectedStatus)
      setSavedStatus(selectedStatus)
      onUpdated?.(selectedStatus)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update')
    } finally {
      setSaving(false)
    }
  }

  const current = STATUS_OPTIONS.find((s) => s.value === selectedStatus)

  if (loading) {
    return (
      <div className="card mb-4">
        <p className="text-secondary text-sm">Loading status...</p>
      </div>
    )
  }

  return (
    <div className="card mb-4">
      <div className="flex-between mb-4">
        <div className="flex-center gap-sm">
          <h3 className="heading-sm">My Status</h3>
          <span className={`status-dot ${current?.dotClass ?? 'status-dot-offline'}`} />
        </div>
        <span className="text-secondary text-sm">{current?.label}</span>
      </div>

      <div className="presence-options">
        {STATUS_OPTIONS.map((opt) => {
          const isSelected = selectedStatus === opt.value
          return (
            <button
              key={opt.value}
              type="button"
              className={`presence-btn ${isSelected ? opt.activeClass : ''}`}
              onClick={() => setSelectedStatus(opt.value)}
              disabled={saving}
            >
              <span className={`status-dot ${opt.dotClass}`} />
              <span className="presence-btn-label">{opt.label}</span>
            </button>
          )
        })}
      </div>

      {dirty && (
        <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={handleSubmit}
            disabled={saving}
          >
            {saving ? 'Saving...' : saved ? 'Saved!' : 'Submit'}
          </button>
          <span style={{ fontSize: '0.8rem', color: 'var(--color-warning)' }}>
            Unsaved — click Submit to apply
          </span>
        </div>
      )}

      {error && (
        <p className="text-danger text-sm mt-3">{error}</p>
      )}
    </div>
  )
}
